# Trading Engine

**This topic moved to the private `DexterBrandonJr/trading-engine`
repository**, at `.claude/memory/topics/trading-engine.md`.

## Why

Entries here named a real account balance, per-trade dollar figures, and live
tickers. This repository is **public** — it renders as Dex's GitHub profile.
That was my mistake across several sessions, not a decision anyone made.
Trading memory belongs with the private trading repo, so that is where it now
lives and where new entries go.

## What this does and does not fix

It stops the exposure growing. It does **not** remove what is already there.

## A history rewrite would NOT fix it — checked 2026-09-10

This file previously listed "rewrite history on this path" as an option. That
was wrong, and acting on it would have been worse than doing nothing.

GitHub keeps `refs/pull/<n>/head` for every pull request ever opened. Those
refs are **read-only and controlled by GitHub** — a force-push to `main`
cannot touch them. Verified directly:

    git fetch origin refs/pull/6/head
    # reaches 25b7393 and 14679e9, which carry the figures

So a rewrite would have rewritten every commit on `main`, invalidated existing
clones, and left the content fetchable through the PR refs and visible in that
pull request's "Files changed" tab — while creating the appearance of a fix.
The appearance is the dangerous part.

## What would actually work

- **Make this repository private.** Removes public access to everything
  including the PR refs, immediately. Cost: the profile README stops rendering
  on the GitHub profile page, which is this repo's whole purpose.
- **Delete and recreate the repository.** Purges the PR refs with everything
  else. Cost: loses the pull request history, which is real work product.
- **Ask GitHub to purge the refs.** The only option that keeps both the repo
  public and its history.
- **Accept it.** Paper-stage figures on a small account, and the account
  identifiers themselves were never published — only balances and tickers.

Dex's call. Nothing destructive has been done, and the rewrite specifically
should not be attempted by a future session believing it will help.

## Reading it

Open `.claude/memory/topics/trading-engine.md` in the `trading-engine`
repository.

## 2026-10-16 — The decision machine: the F1 Clash eight habits mapped onto the engine

**Decisions:**
- **Carry the F1 Clash duel method over as a process, not as numbers** (Dex, Oct 16). The eight habits: one memory read first and written last; mechanics before models; cheap structured observation; a ledger before every change; a gate before every experiment; every loss bucketed execution / plan / opponent; per-regime cards revised on evidence; honest calibration.
- **The spec is `docs/DECISION_MACHINE.md` in the engine's repo.** Six of the eight habits already exist as modules. The gap is a run that ends: nothing has closed since mid-September, so the scorer, the drift detector and the self-review wait on an empty ledger every morning.
- **Next build, on Dex's go: the shadow duel.** `findings` and `experiments` tables in the F1 Clash shape, a resolve-time writer that buckets each shadow loss, Brier by setup kind and by regime. The shadow book's rows become finished duels on day one. Nothing moves money.

**Facts / preferences:**
- F1 Clash's record is why this transfers: 79 duels in two weeks with every one logged, and the win rate against stronger rivals moved while the car did not.
- What does not transfer: the game's win rates, and the cycle time. A spread takes days; the shadow book is the only honest way to shorten it.
- Observation (Claude in Chrome, the Mac as a data miner) is not the engine's bottleneck. Closing is.

**Artifacts:**
- `docs/DECISION_MACHINE.md` (trading-engine, pull request 175)
- hub raw 1743, benchmark row, thread t:1549

**Open threads:**
- t:1549: the shadow-duel pull request after Dex says go.
