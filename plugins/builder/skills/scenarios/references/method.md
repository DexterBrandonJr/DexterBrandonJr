# The method, and why each rule is there

## Draws that can be checked

Every uniform number is `(first 8 hex digits of md5("seed:iteration:factor:k") + 0.5) / 2^32`.
A normal draw is Box–Muller on two of them: `sqrt(-2 ln u1) × cos(2π u2)`.
The same spec and seed give the same draws in PostgreSQL and in Python, so
a result from the hub can be re-run on any laptop and must agree. Both
self-tests assert one reference answer: 800 runs, `separated`, 92.625% and
97.375%.

## Arms on the same draws

Each iteration draws every factor once and applies it to every arm (common
random numbers). Two arms then differ only where their settings differ, so
the paired difference has a much smaller spread than two independent
simulations would, and a comparison settles in far fewer runs.

## Averaging chances, not coin flips

For a `probability` outcome each iteration records the chance itself, the
logistic of the predictor, rather than a simulated yes or no. The average of
the chances estimates the same number with less noise (Rao–Blackwell), so it
settles sooner.

## When it stops

Batches of 200 iterations. After each batch, for each arm: the mean `m`, the
sample standard deviation `s`, the half-width `1.96 s / √n`.

| Stop | When |
|---|---|
| `converged` | n ≥ the minimum (400) and every arm's half-width ≤ the tolerance (absolute for chances, relative for averages) |
| `separated` | n ≥ the minimum, the leader's paired difference over the runner-up is more than 3 of its standard errors, and every arm's half-width ≤ twice the tolerance |
| `max-iterations` | n reaches the ceiling (10,000; lower if asked) |
| `time` | the time budget is spent (3 s by default; 2 s in the nightly) |

The minimum keeps an early lucky streak from ending a run. The 3-standard-
error rule is stricter than the usual 2 because the check is repeated after
every batch, and repeated looks inflate false alarms. A run stopped by
`max-iterations` or `time` still reports honest intervals; they are just
wider than the tolerance.

## What moved it

For the first arm, the correlation of each varying factor with the outcome
across iterations. Its square over the sum of squares is that factor's share
of the explained spread (exact when factors are independent and effects are
linear; a fair ranking otherwise). The **speculation share** is the part of
that total carried by emerging or speculative factors. When it is large, run
again with facts only: those factors held at their centre.

## Reality scores it

- **Forecasts.** An arm's chance goes on the forecast ledger with a due date
  and is Brier-scored when it settles: 0 is perfect, 0.25 is a coin flip.
- **Observations.** Each logged outcome, with whatever factor values were
  known (the rest at their centres), is compared with the current model:
  bias (mean miss), spread of the misses, root-mean-square error, and Brier
  for chances. When at least five misses lean one way by more than two
  standard errors, the hub proposes a recalibration on its backlog.
- **Across scenarios.** `sc_domain_weight` ranks the domains by how often
  they land in a scenario's top three. It shows which levers matter across
  everything, not only in one question.

## What it cannot do

It cannot know an effect it was not given. A factor missing from the spec
has no weight, and a wrong effect size produces a confident wrong answer.
That is why every effect carries a basis, every run can end on the ledger,
and every observation is kept. The noise term is the honest name for
everything not yet named.
