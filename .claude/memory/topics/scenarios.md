# Scenarios

## 2026-09-26 — Scenarios: a what-if engine that stops when the answer is settled

**Decisions:**
- A scenario is one question, one outcome, the factors that move it (each with a distribution, a domain and an evidence status), terms that say how much, and up to six arms to compare. The engine stops the moment the answer is settled: every arm's 95% interval inside the tolerance (converged), or the leader three paired standard errors ahead with every arm inside twice the tolerance (separated); otherwise at 10,000 runs or the time budget.
- Arms share every random draw, and probability runs average the chance itself, so comparisons settle in hundreds of runs instead of thousands.
- A future or doubtful factor can never pass as fact: a factor under an emerging or speculative domain cannot be labeled measured or estimated, and every run reports the share of its answer resting on those factors. A facts-only run holds them at their centre.
- The simulation never runs in a chat. One spec, one run call, one short report; a hub re-runs stale scenarios inside its database with no model tokens.
- The honest limit, stated once in the skill: a simulation reports the consequences of its model; reality scores it (forecasts on a ledger, observations against the model).

**Facts / preferences:**
- Tested: the Python engine's self-test (22 checks) and the hub's SQL self-test both assert one reference answer (800 runs, separated, 92.625% and 97.375%), and both give it: the draws come from md5(seed:iteration:factor:k), so the two engines agree to 15 significant digits.
- Worst case (24 factors, 6 arms): 10,000 runs in 2.9 s in Python and 8.7 s in the database; the two worked examples settle in 400 to 1,000 runs.

**Artifacts:**
- `.claude/skills/scenarios/`: SKILL.md, `scripts/scenarios.py` (validate, run, save, to-hub, domains, selftest), `references/domains.json` (129 nodes in 16 groups, body to cosmos and emerging), `references/spec.md`, `references/method.md`, `examples/` (a night crew of 3 or 4; a training day by time and partner).

**Open threads:**
- The examples run on illustrative effect sizes, labeled as such; real observations replace them.
