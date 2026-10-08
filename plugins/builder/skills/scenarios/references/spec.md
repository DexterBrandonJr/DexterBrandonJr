# The scenario spec

One JSON object. The hub (`hub_scenario`) and the Python engine
(`scripts/scenarios.py validate`) apply the same rules: a spec that breaks one
is refused with the reason, never repaired.

```json
{
  "slug": "night-response-crew",
  "name": "Night response: a crew of 3 or 4",
  "question": "Chance the first crew is working on scene within 8 minutes",
  "subject": "fire-service",
  "note": "free text",
  "outcome": {"kind": "value", "unit": "min", "intercept": 5.0, "noise_sd": 0.9,
              "target": 8, "target_dir": "le", "better": "higher"},
  "tol": 0.01,
  "factors": [
    {"key": "sleep_debt", "domain": "body.sleep", "unit": "h", "status": "estimated",
     "basis": "where the numbers came from", "dist": {"kind": "triangular", "min": 0, "mode": 1.5, "max": 6}}
  ],
  "terms": [
    {"factor": "sleep_debt", "form": "linear", "effect": 0.12, "center": 0, "basis": "illustrative"}
  ],
  "arms": [
    {"arm": "crew-3", "set": {"crew_size": 3}},
    {"arm": "crew-4", "set": {"crew_size": {"kind": "fixed", "value": 4}}}
  ]
}
```

## Fields

| Field | Rule |
|---|---|
| `slug` | 2 to 63 lowercase letters, digits, dashes; defining the same slug again makes a new version |
| `name`, `question` | 4+ and 8+ characters |
| `subject` | optional; in the hub, a subject name or alias |
| `outcome.kind` | `probability`: the linear predictor is on the log-odds scale and the chance is its logistic. `value`: the outcome is the predictor plus normal noise |
| `outcome.base_p` | probability only, instead of `intercept`: the starting chance, 0 to 1 exclusive |
| `outcome.intercept` | the predictor's starting value (default 0) |
| `outcome.noise_sd` | value only: what the named factors do not explain (default 0) |
| `outcome.target`, `target_dir` | value only: turns it into a chance of `le` (at most) or `ge` (at least) the target |
| `outcome.better` | `higher` (default) or `lower`: which arm counts as best |
| `tol` | the half-width of the 95% interval that counts as settled: absolute for chances (0.01 = one point), relative for averages (0.01 = 1%) |
| `factors` | 1 to 24; `key` lowercase, unique; `domain` from the catalog; `status` optional (see below); `basis` required when `measured` |
| `terms` | 1 to 48; each adds to the predictor |
| `arms` | 0 to 6; none means one arm called `base` |

## Evidence status

| Status | Means | Allowed when |
|---|---|---|
| `measured` | observed now: the person's data or an official source; `basis` names it | domain is not emerging or speculative |
| `estimated` | an effect from research, or a heuristic stated as one (default) | domain is not emerging or speculative |
| `emerging` | not real at scale yet (default under `emerging.*`) | always |
| `speculative` | claimed, weakly evidenced | always |

A factor can be labeled weaker than its domain, never stronger.

## Distributions

A plain number is `{"kind": "fixed", "value": n}`. Any kind takes `lo` and
`hi` to clamp.

| kind | parameters | draw |
|---|---|---|
| `fixed` | `value` | always the value |
| `uniform` | `min` < `max` | evenly between |
| `normal` | `mean`, `sd` > 0 | bell curve |
| `lognormal` | `median` > 0, `sigma` > 0 | right-skewed, never negative: times, distances, costs |
| `triangular` | `min` <= `mode` <= `max`, `min` < `max` | a best guess with a range |
| `bernoulli` | `p` in 0..1 | 1 with chance p, else 0 |
| `choice` | `values`, optional `weights` (positive) | one of the listed values |
| `empirical` | `values` (1 to 1,000); optional `from`: `checkins.mood`, `checkins.energy`, `checkins.confidence` | one of the values, evenly; with `from`, the hub uses the latest 60 check-ins when there are five or more, else the values |

## Terms

| form | adds |
|---|---|
| `linear` | effect × (x − center) |
| `quadratic` | effect × (x − center)²: an inverted U with a negative effect |
| `step` | effect when x ≥ threshold |
| `step_below` | effect when x < threshold |
| `interaction` | effect × (x − center) × (x2 − center2), with `factor2` |

For a `probability` outcome the effects are log-odds: +0.4 moves a 50%
chance to about 60%, and a 90% chance to about 93%.

## Arms

`set` maps factor keys to a number or a distribution. Everything not set
keeps the factor's own distribution. Arms share every random draw, so the
difference between two arms is measured on the same simulated days.
