#!/usr/bin/env python3
"""scenarios.py: the Scenarios engine, portable. Standard library only, Python 3.8+.

A scenario is one question with one outcome, the factors that move it (each
with a distribution, a domain from references/domains.json and an evidence
status), the terms that say how much each factor moves it, and up to six
arms (configurations) to compare. The engine runs it as a Monte Carlo
simulation and stops as soon as the answer is settled:

    python3 scenarios.py validate spec.json
    python3 scenarios.py run spec.json                 # report in plain text
    python3 scenarios.py run spec.json --save scenarios/   # also keep spec + a summary line forever
    python3 scenarios.py run spec.json --facts-only    # emerging and speculative factors held at their centre
    python3 scenarios.py to-hub spec.json              # the SQL that stores it in a hub with 0017_scenarios
    python3 scenarios.py domains [prefix]              # the catalog
    python3 scenarios.py selftest

Halting: batches of 200 iterations, at least 400, at most 10,000, within a
time budget (3 s by default). It stops early when every arm's 95% interval
is narrower than the tolerance (converged), or when the best arm leads the
runner-up by more than three standard errors of the paired difference and
every arm is known to within twice the tolerance (separated). Arms share random numbers (common random numbers), so a
comparison settles in far fewer runs than two independent simulations.

Random numbers come from md5(seed:iteration:factor:k), so a run is
reproducible, and the hub's SQL engine (migration 0017_scenarios) draws the
exact same numbers: the same spec and seed give the same answer in both,
which the self-tests of both engines check against one reference.

Only summaries are stored, never iterations: a run is one line of JSON.
"""
import argparse, hashlib, json, math, os, pathlib, re, sys, time

HERE = pathlib.Path(__file__).resolve().parent
DOMAINS_FILE = HERE.parent / "references" / "domains.json"
MAX_ITER_CAP = 10000
KINDS = ("fixed", "uniform", "normal", "lognormal", "triangular", "bernoulli", "choice", "empirical")
FORMS = ("linear", "quadratic", "step", "step_below", "interaction")
STATUSES = ("measured", "estimated", "emerging", "speculative")
WEAK = ("emerging", "speculative")
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{1,62}$")
KEY = re.compile(r"^[a-z][a-z0-9_]{0,40}$")
ARM = re.compile(r"^[a-z0-9][a-z0-9_-]{0,40}$")


class SpecError(ValueError):
    pass


# --- the catalog -------------------------------------------------------------
def load_domains(path=None):
    data = json.load(open(path or DOMAINS_FILE, encoding="utf-8"))
    return {d["id"]: d for d in data["domains"]}


# --- random numbers, identical to the SQL engine ----------------------------
def u(seed, i, key, k):
    h = hashlib.md5(f"{seed}:{i}:{key}:{k}".encode()).hexdigest()[:8]
    return (int(h, 16) + 0.5) / 4294967296.0


def gauss(u1, u2):
    return math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)


# --- distributions -----------------------------------------------------------
def _num(v, what):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        raise SpecError(f"{what} must be a number")
    return float(v)


def dist_from_spec(d, where):
    """Normalise a distribution to {kind, p1, p2, p3, lo, hi, vals, cum, src}."""
    if isinstance(d, (int, float)) and not isinstance(d, bool):
        d = {"kind": "fixed", "value": d}
    if not isinstance(d, dict):
        raise SpecError(f"{where}: a distribution is a number or an object with a kind")
    k = d.get("kind")
    if k not in KINDS:
        raise SpecError(f"{where}: kind must be one of {', '.join(KINDS)}")
    out = {"kind": k, "p1": None, "p2": None, "p3": None, "lo": None, "hi": None, "vals": None, "cum": None, "src": None}
    if k == "fixed":
        out["p1"] = _num(d.get("value"), f"{where}: value")
    elif k == "uniform":
        out["p1"], out["p2"] = _num(d.get("min"), f"{where}: min"), _num(d.get("max"), f"{where}: max")
        if not out["p1"] < out["p2"]:
            raise SpecError(f"{where}: uniform needs min < max")
    elif k == "normal":
        out["p1"], out["p2"] = _num(d.get("mean"), f"{where}: mean"), _num(d.get("sd"), f"{where}: sd")
        if out["p2"] <= 0:
            raise SpecError(f"{where}: normal needs sd > 0")
    elif k == "lognormal":
        out["p1"], out["p2"] = _num(d.get("median"), f"{where}: median"), _num(d.get("sigma"), f"{where}: sigma")
        if out["p1"] <= 0 or out["p2"] <= 0:
            raise SpecError(f"{where}: lognormal needs median > 0 and sigma > 0")
    elif k == "triangular":
        a, m, b = (_num(d.get(x), f"{where}: {x}") for x in ("min", "mode", "max"))
        if not (a <= m <= b and a < b):
            raise SpecError(f"{where}: triangular needs min <= mode <= max and min < max")
        out["p1"], out["p2"], out["p3"] = a, m, b
    elif k == "bernoulli":
        out["p1"] = _num(d.get("p"), f"{where}: p")
        if not 0 <= out["p1"] <= 1:
            raise SpecError(f"{where}: bernoulli needs 0 <= p <= 1")
    elif k == "choice":
        vals = d.get("values") or []
        w = d.get("weights") or [1] * len(vals)
        if not vals or len(vals) > 1000 or len(w) != len(vals):
            raise SpecError(f"{where}: choice needs 1 to 1000 values and one weight per value")
        vals = [_num(v, f"{where}: value") for v in vals]
        w = [_num(x, f"{where}: weight") for x in w]
        if any(x <= 0 for x in w):
            raise SpecError(f"{where}: choice weights must be positive")
        total, acc, cum = 0.0, 0.0, []
        for x in w:
            total += x
        for x in w:
            acc += x
            cum.append(acc / total)
        cum[-1] = 1.0
        out["vals"], out["cum"] = vals, cum
    elif k == "empirical":
        vals = d.get("values") or []
        if not vals or len(vals) > 1000:
            raise SpecError(f"{where}: empirical needs 1 to 1000 values (the fallback when 'from' has too few)")
        out["vals"] = [_num(v, f"{where}: value") for v in vals]
        if d.get("from") is not None:
            if d["from"] not in ("checkins.mood", "checkins.energy", "checkins.confidence"):
                raise SpecError(f"{where}: from must be checkins.mood, checkins.energy or checkins.confidence")
            out["src"] = d["from"]
    if "lo" in d and d["lo"] is not None:
        out["lo"] = _num(d["lo"], f"{where}: lo")
    if "hi" in d and d["hi"] is not None:
        out["hi"] = _num(d["hi"], f"{where}: hi")
    if out["lo"] is not None and out["hi"] is not None and out["lo"] > out["hi"]:
        raise SpecError(f"{where}: lo must be <= hi")
    return out


def clamp(x, d):
    lo = -math.inf if d["lo"] is None else d["lo"]
    hi = math.inf if d["hi"] is None else d["hi"]
    return min(hi, max(lo, x))


def transform(d, u1, u2):
    k = d["kind"]
    p1, p2, p3 = d["p1"], d["p2"], d["p3"]
    if k == "fixed":
        x = p1
    elif k == "uniform":
        x = p1 + (p2 - p1) * u1
    elif k == "normal":
        x = p1 + p2 * gauss(u1, u2)
    elif k == "lognormal":
        x = p1 * math.exp(p2 * gauss(u1, u2))
    elif k == "triangular":
        c = (p2 - p1) / (p3 - p1) if p3 != p1 else None
        if c is not None and u1 < c:
            x = p1 + math.sqrt(u1 * (p3 - p1) * (p2 - p1))
        else:
            x = p3 - math.sqrt((1 - u1) * (p3 - p1) * (p3 - p2))
    elif k == "bernoulli":
        x = 1.0 if u1 < p1 else 0.0
    elif k == "choice":
        x = next(v for v, w in zip(d["vals"], d["cum"]) if w >= u1)
    elif k == "empirical":
        x = d["vals"][int(math.floor(u1 * len(d["vals"])))]
    return clamp(x, d)


def center(d):
    k = d["kind"]
    p1, p2, p3 = d["p1"], d["p2"], d["p3"]
    if k in ("fixed", "normal", "lognormal", "bernoulli"):
        x = p1
    elif k == "uniform":
        x = (p1 + p2) / 2
    elif k == "triangular":
        x = (p1 + p2 + p3) / 3
    elif k == "choice":
        prev, x = 0.0, 0.0
        for v, w in zip(d["vals"], d["cum"]):
            x += v * (w - prev)
            prev = w
    else:
        x = sum(d["vals"]) / len(d["vals"])
    return clamp(x, d)


# --- the spec ----------------------------------------------------------------
def normalize(spec, domains=None):
    """Validate a spec and return the model the engine runs. Refuses, never repairs."""
    domains = domains if domains is not None else load_domains()
    if not isinstance(spec, dict):
        raise SpecError("a spec is a JSON object")
    slug = spec.get("slug", "")
    if not isinstance(slug, str) or not SLUG.match(slug):
        raise SpecError("slug: 2 to 63 lowercase letters, digits and dashes")
    name, question = spec.get("name") or "", spec.get("question") or ""
    if len(name.strip()) < 4 or len(question.strip()) < 8:
        raise SpecError("a scenario needs a name (4+ characters) and a question (8+ characters)")
    o = spec.get("outcome") or {}
    kind = o.get("kind")
    if kind not in ("probability", "value"):
        raise SpecError("outcome.kind: probability or value")
    if "base_p" in o and o["base_p"] is not None:
        bp = _num(o["base_p"], "outcome.base_p")
        if not 0 < bp < 1:
            raise SpecError("outcome.base_p must be between 0 and 1, exclusive")
        intercept = math.log(bp / (1 - bp))
    else:
        intercept = _num(o.get("intercept", 0), "outcome.intercept")
    noise_sd = _num(o.get("noise_sd", 0), "outcome.noise_sd")
    if noise_sd < 0:
        raise SpecError("outcome.noise_sd must be >= 0")
    target = o.get("target")
    target_dir = o.get("target_dir")
    if kind == "value" and target is not None:
        target = _num(target, "outcome.target")
        if target_dir not in ("le", "ge"):
            raise SpecError("outcome.target_dir: le (at most the target) or ge (at least the target)")
    else:
        target, target_dir = None, None
    better = o.get("better", "higher")
    if better not in ("higher", "lower"):
        raise SpecError("outcome.better: higher or lower")
    tol = _num(spec.get("tol", 0.01), "tol")
    if tol <= 0:
        raise SpecError("tol must be > 0")

    fs = spec.get("factors") or []
    if not 1 <= len(fs) <= 24:
        raise SpecError("1 to 24 factors")
    factors, seen = [], set()
    for n, f in enumerate(fs, 1):
        key = f.get("key", "")
        if not isinstance(key, str) or not KEY.match(key) or key in seen:
            raise SpecError(f"factor {n}: key must be unique, lowercase, start with a letter")
        seen.add(key)
        dom = f.get("domain")
        if dom not in domains:
            raise SpecError(f"factor {key}: unknown domain '{dom}' (see references/domains.json)")
        dstat = domains[dom]["status"]
        weak_domain = dstat in WEAK or dom == "emerging" or dom.startswith("emerging.")
        given = f.get("status")
        if given is not None and given not in STATUSES:
            raise SpecError(f"factor {key}: status must be one of {', '.join(STATUSES)}")
        if weak_domain:
            default = dstat if dstat in WEAK else "emerging"
            status = given or default
            if status not in WEAK:
                raise SpecError(f"factor {key}: a factor under the {default} domain {dom} cannot be labeled {status}")
        else:
            status = given or "estimated"
        basis = (f.get("basis") or "").strip()
        if status == "measured" and not basis:
            raise SpecError(f"factor {key}: measured needs a basis (where the numbers came from)")
        factors.append({"key": key, "domain": dom, "status": status, "dist": dist_from_spec(f.get("dist"), f"factor {key}"),
                        "unit": f.get("unit"), "basis": basis or None})
    keys = {f["key"] for f in factors}

    ts = spec.get("terms") or []
    if not 1 <= len(ts) <= 48:
        raise SpecError("1 to 48 terms")
    terms = []
    for n, t in enumerate(ts, 1):
        form = t.get("form", "linear")
        if form not in FORMS:
            raise SpecError(f"term {n}: form must be one of {', '.join(FORMS)}")
        f1, f2 = t.get("factor"), t.get("factor2")
        if f1 not in keys:
            raise SpecError(f"term {n}: unknown factor '{f1}'")
        if form == "interaction" and f2 not in keys:
            raise SpecError(f"term {n}: an interaction needs factor2, a known factor")
        if form != "interaction":
            f2 = None
        thr = t.get("threshold")
        if form in ("step", "step_below"):
            thr = _num(thr, f"term {n}: threshold")
        else:
            thr = None
        terms.append({"form": form, "f1": f1, "f2": f2, "effect": _num(t.get("effect"), f"term {n}: effect"),
                      "center": _num(t.get("center", 0), f"term {n}: center"), "center2": _num(t.get("center2", 0), f"term {n}: center2"),
                      "threshold": thr, "basis": t.get("basis")})

    arms_in = spec.get("arms") or []
    if len(arms_in) > 6:
        raise SpecError("at most 6 arms")
    arms, names = [], set()
    for n, a in enumerate(arms_in, 1):
        nm = a.get("arm", "")
        if not isinstance(nm, str) or not ARM.match(nm) or nm in names:
            raise SpecError(f"arm {n}: a unique lowercase name")
        names.add(nm)
        sets = {}
        for k, v in (a.get("set") or {}).items():
            if k not in keys:
                raise SpecError(f"arm {nm}: unknown factor '{k}'")
            sets[k] = dist_from_spec(v, f"arm {nm}, factor {k}")
        arms.append({"arm": nm, "sets": sets, "note": a.get("note")})
    if not arms:
        arms = [{"arm": "base", "sets": {}, "note": None}]
    return {"slug": slug, "name": name.strip(), "question": question.strip(), "subject": spec.get("subject"),
            "kind": kind, "unit": o.get("unit"), "intercept": intercept, "noise_sd": noise_sd, "target": target,
            "target_dir": target_dir, "better": better, "tol": tol, "factors": factors, "terms": terms, "arms": arms}


# --- statistics, matching PostgreSQL's aggregates ---------------------------
def mean(xs):
    return sum(xs) / len(xs)


def sd(xs):
    if len(xs) < 2:
        return None
    m = mean(xs)
    return math.sqrt(sum((x - m) * (x - m) for x in xs) / (len(xs) - 1))


def percentile_cont(xs, p):
    s = sorted(xs)
    pos = p * (len(s) - 1)
    lo = int(math.floor(pos))
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def corr(xs, ys):
    mx, my = mean(xs), mean(ys)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) * (x - mx) for x in xs)
    syy = sum((y - my) * (y - my) for y in ys)
    if sxx <= 0 or syy <= 0:
        return None
    return sxy / math.sqrt(sxx * syy)


# --- the run -----------------------------------------------------------------
def term_value(t, x):
    a = x[t["f1"]]
    f = t["form"]
    if f == "linear":
        return t["effect"] * (a - t["center"])
    if f == "quadratic":
        return t["effect"] * (a - t["center"]) * (a - t["center"])
    if f == "step":
        return t["effect"] if a >= t["threshold"] else 0.0
    if f == "step_below":
        return t["effect"] if a < t["threshold"] else 0.0
    return t["effect"] * (a - t["center"]) * (x[t["f2"]] - t["center2"])


def run(model, seed=1, max_iter=MAX_ITER_CAP, budget_ms=3000, tol=None, min_iter=400, batch=200, facts_only=False, clock=time.monotonic):
    max_iter = max(1, min(int(max_iter), MAX_ITER_CAP))
    min_iter = max(1, min(int(min_iter), max_iter))
    batch = max(50, min(int(batch), 1000))
    tol = float(tol) if tol else model["tol"]
    prob = model["kind"] == "probability"
    metric = "p" if prob else ("p_target" if model["target"] is not None else "mean")
    arms = model["arms"]
    names = [a["arm"] for a in arms]
    ys = {a: [] for a in names}
    ms = {a: [] for a in names}
    first = names[0]
    xs_first = {f["key"]: [] for f in model["factors"]}
    # a factor needs a second uniform when its distribution, or any arm's, is normal or lognormal
    needs_u2 = {f["key"]: f["dist"]["kind"] in ("normal", "lognormal") or any(
        a["sets"].get(f["key"], {}).get("kind") in ("normal", "lognormal") for a in arms) for f in model["factors"]}
    n, trace, halted = 0, [], None
    t0 = clock()
    while True:
        b = min(batch, max_iter - n)
        for i in range(n + 1, n + b + 1):
            # uniforms once per iteration and factor, shared by every arm (common random numbers)
            us = {f["key"]: (u(seed, i, f["key"], 1), u(seed, i, f["key"], 2) if needs_u2[f["key"]] else 0.5) for f in model["factors"]}
            for arm in arms:
                x = {}
                for f in model["factors"]:
                    d = arm["sets"].get(f["key"], f["dist"])
                    if facts_only and f["status"] in WEAK:
                        v = center(d)
                    else:
                        v = transform(d, *us[f["key"]])
                    x[f["key"]] = v
                lp = model["intercept"]
                for t in model["terms"]:
                    lp += term_value(t, x)
                if prob:
                    y = 1.0 / (1.0 + math.exp(-max(min(lp, 700.0), -700.0)))
                    m = y
                else:
                    y = lp + model["noise_sd"] * gauss(u(seed, i, "~noise", 1), u(seed, i, "~noise", 2))
                    if model["target"] is not None:
                        hit = y <= model["target"] if model["target_dir"] == "le" else y >= model["target"]
                        m = 1.0 if hit else 0.0
                    else:
                        m = y
                ys[arm["arm"]].append(y)
                ms[arm["arm"]].append(m)
                if arm["arm"] == first:
                    for k, v in x.items():
                        xs_first[k].append(v)
        n += b
        stats = {}
        for a in names:
            mu, s = mean(ms[a]), sd(ms[a])
            hw = 1.96 * s / math.sqrt(n) if s is not None else math.inf
            thr = tol if metric in ("p", "p_target") else tol * max(abs(mu), 1e-9)
            stats[a] = (mu, s, hw, thr)
        converged = all(stats[a][2] <= stats[a][3] for a in names)
        order = sorted(names, key=lambda a: ((-stats[a][0]) if model["better"] == "higher" else stats[a][0], names.index(a)))
        best = order[0]
        second = order[1] if len(order) > 1 else None
        separated, diff, se_d = False, None, None
        if second is not None:
            d = [p - q for p, q in zip(ms[best], ms[second])]
            diff = mean(d)
            sd_d = sd(d)
            se_d = sd_d / math.sqrt(n) if sd_d is not None else None
            separated = (se_d == 0 and diff != 0) or (se_d is not None and se_d > 0 and abs(diff) > 3 * se_d)
        trace.append([n, stats[best][0], max(stats[a][2] for a in names)])
        elapsed = (clock() - t0) * 1000
        # a settled ranking also needs every arm known to within twice the tolerance
        settled = separated and all(stats[a][2] <= 2 * stats[a][3] for a in names)
        if n >= min_iter and (converged or settled):
            halted = "converged" if converged else "separated"
            break
        if n >= max_iter:
            halted = "max-iterations"
            break
        if elapsed > budget_ms:
            halted = "time"
            break
    out_arms = []
    for a in names:
        mu, s, hw, _ = stats[a]
        se = s / math.sqrt(n) if s is not None else None
        out_arms.append({"arm": a, "n": n, "est": mu, "lo": mu - 1.96 * se if se is not None else None,
                         "hi": mu + 1.96 * se if se is not None else None, "mean_y": mean(ys[a]),
                         "p10": percentile_cont(ys[a], 0.1), "p50": percentile_cont(ys[a], 0.5), "p90": percentile_cont(ys[a], 0.9)})
    sens = []
    status = {f["key"]: f for f in model["factors"]}
    for k, vals in xs_first.items():
        c = corr(vals, ys[first]) if len(vals) > 1 else None
        if c is not None:
            sens.append({"key": k, "domain": status[k]["domain"], "status": status[k]["status"], "corr": c})
    total = sum(s["corr"] * s["corr"] for s in sens)
    for s in sens:
        s["share"] = s["corr"] * s["corr"] / total if total > 0 else 0.0
    sens.sort(key=lambda s: (-s["share"], s["key"]))
    spec_share = sum(s["share"] for s in sens if s["status"] in WEAK) if sens else None
    lead = lead_lo = lead_hi = None
    if second is not None:
        lead = diff
        lead_lo = diff - 1.96 * se_d if se_d is not None else None
        lead_hi = diff + 1.96 * se_d if se_d is not None else None
    return {"slug": model["slug"], "seed": seed, "iterations": n, "halted": halted, "ms": int((clock() - t0) * 1000),
            "metric": metric, "arms": out_arms, "best": best, "second": second, "lead": lead, "lead_lo": lead_lo,
            "lead_hi": lead_hi, "sensitivity": sens, "speculation_share": spec_share, "trace": trace,
            "settings": {"max_iter": max_iter, "min_iter": min_iter, "batch": batch, "budget_ms": budget_ms, "tol": tol,
                         "z_sep": 3, "facts_only": facts_only, "engine": "python"},
            "run_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}


# --- reading a result --------------------------------------------------------
def fmt(model, v):
    if v is None:
        return "n/a"
    if model["kind"] == "probability" or model["target"] is not None:
        return f"{100 * v:.1f}%"
    return f"{v:,.2f}{(' ' + model['unit']) if model.get('unit') else ''}"


def report(model, r):
    what = "chance" if r["metric"] in ("p", "p_target") else "average"
    lines = [f"Scenario {model['slug']} · {model['question']}",
             f"{r['iterations']:,} runs · {r['halted']} · {r['ms']} ms · seed {r['seed']}" + (" · facts only" if r["settings"].get("facts_only") else "")]
    order = sorted(r["arms"], key=lambda a: -a["est"] if model["better"] == "higher" else a["est"])
    for a in order:
        mark = "  ← best" if a["arm"] == r["best"] and len(order) > 1 else ""
        lines.append(f"- {a['arm']}: {what} {fmt(model, a['est'])} ({fmt(model, a['lo'])} to {fmt(model, a['hi'])}){mark}")
    if r["second"]:
        pts = (lambda v: f"{100 * v:+.1f} points") if r["metric"] in ("p", "p_target") else (lambda v: f"{v:+.2f}")
        lines.append(f"lead over {r['second']}: {pts(r['lead'])} ({pts(r['lead_lo'])} to {pts(r['lead_hi'])}), same random draws on both arms")
    top = r["sensitivity"][:3]
    if top:
        lines.append("moves it most: " + " · ".join(f"{s['key']} {s['corr']:+.2f} ({s['status']})" for s in top))
    if r["speculation_share"] is not None:
        lines.append(f"resting on emerging or speculative factors: {100 * r['speculation_share']:.0f}% of the spread")
    return "\n".join(lines)


# --- storage: the spec once, one line per run, forever ----------------------
def save(model, spec, r, root):
    d = pathlib.Path(root) / model["slug"]
    d.mkdir(parents=True, exist_ok=True)
    (d / "spec.json").write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with open(d / "runs.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    return d


def to_hub(spec, author="claude:code"):
    body = json.dumps(spec, ensure_ascii=False)
    tag = "$sc$"
    while tag in body:
        tag = tag[:-1] + "x$"
    return (f"select * from hub_scenario({tag}{body}{tag}::jsonb, '{author}');\n"
            f"select * from hub_scenario_run('{spec['slug']}');")


def domains_sql():
    def q(v):
        return "null" if v is None else "'" + str(v).replace("'", "''") + "'"
    rows = []
    for d in load_domains().values():
        parent = d["id"].rsplit(".", 1)[0] if "." in d["id"] else None
        rows.append("  (%s, %s, %s, %s, %s, %s, %s, %s, %s)" % (q(d["id"]), q(parent), q(d["name"]), q(d["status"]), q(d.get("unit")),
                                                             q(d["note"]), q(d.get("source")), q(d.get("horizon")),
                                                             "null" if d.get("p_real") is None else repr(d["p_real"])))
    return ("insert into sc_domains (id, parent, name, status, unit, note, source, horizon, p_real) values\n" + ",\n".join(rows) +
            "\non conflict (id) do update set name = excluded.name, status = excluded.status, unit = excluded.unit, note = excluded.note,\n"
            "  source = excluded.source, horizon = excluded.horizon, p_real = excluded.p_real;")


# --- self-test ---------------------------------------------------------------
REFERENCE = {
    "slug": "ref-all-kinds", "name": "Reference: every kind and form", "question": "Chance the task finishes within 8 minutes",
    "outcome": {"kind": "value", "unit": "min", "intercept": 6, "noise_sd": 0.7, "target": 8, "target_dir": "le", "better": "higher"},
    "tol": 0.01,
    "factors": [
        {"key": "a", "domain": "mind.stress", "dist": {"kind": "normal", "mean": 0, "sd": 1}},
        {"key": "b", "domain": "task.complexity", "dist": {"kind": "uniform", "min": 0, "max": 10}},
        {"key": "c", "domain": "body.sleep", "dist": {"kind": "triangular", "min": 0, "mode": 2, "max": 6}},
        {"key": "d", "domain": "task.distance", "dist": {"kind": "lognormal", "median": 2, "sigma": 0.3, "hi": 5}},
        {"key": "e", "domain": "time.circadian_low", "dist": {"kind": "bernoulli", "p": 0.3}},
        {"key": "f", "domain": "team.skill_mix", "dist": {"kind": "choice", "values": [1, 2, 3], "weights": [0.5, 0.3, 0.2]}},
        {"key": "g", "domain": "mind.energy", "status": "measured", "basis": "reference values", "dist": {"kind": "empirical", "values": [1, 2, 2, 3, 5]}},
        {"key": "h", "domain": "team.size", "dist": {"kind": "fixed", "value": 4}},
        {"key": "w", "domain": "emerging.biosensor_coaching", "dist": {"kind": "bernoulli", "p": 0.5}},
    ],
    "terms": [
        {"factor": "a", "form": "linear", "effect": 0.5},
        {"factor": "b", "form": "linear", "effect": 0.1, "center": 5},
        {"factor": "c", "form": "quadratic", "effect": 0.05, "center": 2},
        {"factor": "d", "form": "linear", "effect": 0.8, "center": 2},
        {"factor": "e", "form": "step", "effect": 0.7, "threshold": 1},
        {"factor": "g", "form": "step_below", "effect": -0.4, "threshold": 2},
        {"factor": "f", "form": "linear", "effect": 0.3, "center": 2},
        {"factor": "a", "form": "interaction", "factor2": "c", "effect": 0.2, "center2": 2},
        {"factor": "h", "form": "linear", "effect": -0.35, "center": 4},
        {"factor": "w", "form": "linear", "effect": -0.3},
    ],
    "arms": [{"arm": "crew-4", "set": {"h": 4}}, {"arm": "crew-6", "set": {"h": {"kind": "uniform", "min": 5, "max": 7}}}],
}
# The answer both engines must give for REFERENCE at seed 1 (the SQL self-test checks the same numbers).
REFERENCE_EXPECT = {"iterations": 800, "halted": "separated", "est": [0.92625, 0.97375],
                    "mean_y": [6.128074039168791, 5.436109405782036], "speculation_share": 0.02485589514197013}


def selftest():
    checks = 0

    def expect(cond, msg):
        nonlocal checks
        checks += 1
        if not cond:
            raise AssertionError(f"FAIL {checks} {msg}")

    doms = load_domains()
    expect(len(doms) >= 100 and all(d["status"] in ("category",) + STATUSES for d in doms.values()), "catalog loads with valid statuses")
    expect(all(0 < u(1, i, "k", 1) < 1 for i in range(1, 200)), "uniforms inside (0, 1)")
    expect(abs(u(1, 1, "a", 1) - (int(hashlib.md5(b"1:1:a:1").hexdigest()[:8], 16) + 0.5) / 2 ** 32) < 1e-15, "uniform is md5(seed:i:key:k)")
    tri = dist_from_spec({"kind": "triangular", "min": 0, "mode": 2, "max": 6}, "t")
    expect(all(0 <= transform(tri, u(3, i, "t", 1), 0.5) <= 6 for i in range(1, 500)), "triangular stays in range")
    ch = dist_from_spec({"kind": "choice", "values": [1, 2, 3], "weights": [0.5, 0.3, 0.2]}, "c")
    expect(ch["cum"][-1] == 1.0 and all(transform(ch, u(3, i, "c", 1), 0.5) in (1, 2, 3) for i in range(1, 500)), "choice returns a listed value")
    cl = dist_from_spec({"kind": "normal", "mean": 0, "sd": 5, "lo": -1, "hi": 1}, "n")
    expect(all(-1 <= transform(cl, u(3, i, "n", 1), u(3, i, "n", 2)) <= 1 for i in range(1, 500)), "lo and hi clamp")
    expect(abs(center(ch) - (1 * 0.5 + 2 * 0.3 + 3 * 0.2)) < 1e-12, "choice centre is its weighted mean")

    def refused(mutate, why):
        s = json.loads(json.dumps(REFERENCE))
        mutate(s)
        try:
            normalize(s, doms)
        except SpecError:
            return expect(True, why)
        expect(False, why)

    refused(lambda s: s["factors"][0].update(domain="body.nowhere"), "unknown domain refused")
    refused(lambda s: s["factors"][8].update(status="measured", basis="x"), "an emerging factor labeled measured is refused")
    refused(lambda s: s["factors"][6].update(basis=""), "measured without a basis is refused")
    refused(lambda s: s["terms"][7].pop("factor2"), "an interaction without factor2 is refused")
    refused(lambda s: s["factors"][2]["dist"].update(mode=9), "a triangular mode outside min..max is refused")
    refused(lambda s: s.update(arms=[{"arm": f"a{i}", "set": {}} for i in range(7)]), "more than six arms refused")

    model = normalize(REFERENCE, doms)
    expect(model["factors"][8]["status"] == "emerging", "a factor under an emerging domain is labeled emerging")
    r1 = run(model, seed=1)
    r2 = run(model, seed=1)
    expect(r1["iterations"] == r2["iterations"] and r1["arms"][0]["est"] == r2["arms"][0]["est"], "same seed, same answer")
    expect(r1["halted"] in ("converged", "separated") and r1["iterations"] < MAX_ITER_CAP, f"halts early ({r1['halted']} at {r1['iterations']})")
    expect(r1["best"] == "crew-6" and r1["lead"] > 0, "the bigger crew is better in the reference")
    expect(r1["speculation_share"] is not None and r1["speculation_share"] > 0, "an emerging factor with an effect shows in the speculation share")
    rf = run(model, seed=1, facts_only=True)
    expect(all(s["key"] != "w" for s in rf["sensitivity"]) and (rf["speculation_share"] or 0) == 0, "facts only holds the emerging factor at its centre")
    one = dict(model, arms=[{"arm": "base", "sets": {}, "note": None}])
    rc = run(one, seed=1, max_iter=50000, tol=1e-9, min_iter=10**6, budget_ms=10**9)
    expect(rc["iterations"] == MAX_ITER_CAP and rc["halted"] == "max-iterations", "10,000 is the ceiling")
    rt = run(model, seed=1, budget_ms=0, min_iter=10**6)
    expect(rt["halted"] == "time" and rt["iterations"] == 200, "a spent time budget stops after one batch")
    if REFERENCE_EXPECT:
        e = REFERENCE_EXPECT
        ok = r1["iterations"] == e["iterations"] and r1["halted"] == e["halted"] and all(
            abs(a["est"] - b) < 1e-12 for a, b in zip(r1["arms"], e["est"])) and all(
            abs(a["mean_y"] - b) < 1e-9 for a, b in zip(r1["arms"], e["mean_y"])) and abs(r1["speculation_share"] - e["speculation_share"]) < 1e-9
        expect(ok, f"matches the reference answer the SQL engine gives: {e}")
    return f"SELFTEST OK · {checks} checks passed · reference: {r1['iterations']} runs, {r1['halted']}, " + \
        ", ".join(f"{a['arm']} {a['est']:.12f}" for a in r1["arms"])


def main(argv=None):
    ap = argparse.ArgumentParser(prog="scenarios.py", description="Scenarios: settle a what-if with as few simulations as it takes.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("validate"); p.add_argument("spec")
    p = sub.add_parser("run"); p.add_argument("spec")
    p.add_argument("--seed", type=int, default=1); p.add_argument("--max", type=int, default=MAX_ITER_CAP)
    p.add_argument("--budget-ms", type=int, default=3000); p.add_argument("--tol", type=float)
    p.add_argument("--min", type=int, default=400); p.add_argument("--facts-only", action="store_true")
    p.add_argument("--save", help="folder to keep spec.json and runs.jsonl under <slug>/"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("to-hub"); p.add_argument("spec"); p.add_argument("--author", default="claude:code")
    p = sub.add_parser("domains"); p.add_argument("prefix", nargs="?", default=""); p.add_argument("--sql", action="store_true", help="print the catalog as an insert for the hub")
    sub.add_parser("selftest")
    a = ap.parse_args(argv)
    if a.cmd == "selftest":
        try:
            print(selftest()); return 0
        except AssertionError as e:
            print(str(e)); return 1
    if a.cmd == "domains" and a.sql:
        print(domains_sql()); return 0
    if a.cmd == "domains":
        for d in load_domains().values():
            if d["id"].startswith(a.prefix):
                extra = f" · {d['horizon']} · p {d['p_real']}" if d["status"] == "emerging" else ""
                print(f"{d['id']:<34} {d['status']:<11} {d['name']}{extra}")
        return 0
    spec = json.load(open(a.spec, encoding="utf-8"))
    try:
        model = normalize(spec)
    except SpecError as e:
        print(f"refused: {e}"); return 1
    if a.cmd == "validate":
        print(f"ok · {len(model['factors'])} factors · {len(model['terms'])} terms · {len(model['arms'])} arm(s)"); return 0
    if a.cmd == "to-hub":
        print(to_hub(spec, a.author)); return 0
    r = run(model, seed=a.seed, max_iter=a.max, budget_ms=a.budget_ms, tol=a.tol, min_iter=a.min, facts_only=a.facts_only)
    if a.save:
        print(f"saved under {save(model, spec, r, a.save)}", file=sys.stderr)
    print(json.dumps(r, indent=1) if a.json else report(model, r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
