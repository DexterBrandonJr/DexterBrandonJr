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

## 2026-10-16 — Every recommendation has a record

**Decisions:**
- **One record for every recommendation** (Dex, Oct 16: compile every ticker recommendation ever given and find which won). Three books already held most of it and never met: the cards, the shadow book and the counterfactual ledger. Migration 0026 joins them into `recommendation_record`, one row per card with one verdict in order of trust: by hand, then the shadow book, then the counterfactual ledger; else `live`, `marking` or `unscored`.
- **`verdicts_by_hand` is written only by a human-driven session.** Cowork on the Mac reads the broker's own history, read only, with evidence required. The engine never writes it.
- **The tally view is dropped before it is recreated**: `create or replace` cannot add a column in the middle of a view, and the live apply said so.

**Facts / preferences:**
- Proven on a throwaway Postgres 16 with all 26 migrations and a seeded card per verdict branch; the full suite passes.
- The month's shape, read live: most recommendations lost; the one thesis with a positive record is small. The numbers live in the hub and the engine, not here.
- The only rows a person must score by hand are the 27 cards that predate both books, 12 of them paper positions that never closed.

**Artifacts:**
- `supabase/migrations/0026_every_recommendation_has_a_record.sql`, `tests/test_every_recommendation_has_a_record.py` (trading-engine pull request 176)
- hub raw 1744, thread t:1550 (the Cowork handoff)

**Open threads:**
- t:1550: Cowork scores the 27 by hand, then hands back.
- Pull request 176 waits on CI and a merge.

## 2026-10-16 — Replay lab

**Decisions:**
- **A resolved shadow card keeps being read** (Dex, Oct 16: "build it", after the Builder chat proposed a replay lab). One reading a day until its horizon ends, in `shadow_book.marks_after`. Its outcome, exit and R never move.
- **Exit rules are compared only on the same cards.** Three rules: the current 2x target with half stop, a quarter stop, and no stop. A card goes in only if every rule could finish on its prices.
- **A replay measures, never changes.** A human decides whether a bracket changes.

**Facts / preferences:**
- Proven, first run on live data: 9 of 113 shadow cards replay today, and all 9 hit their target, so every rule exits them the same way. No rule difference can be measured yet.
- The other 104 need prices past resolution: the Mac bars export now, or two to four weeks of the new daily readings.
- Bars are daily closes, so they miss an intraday touch of a stop or target. The report says so.

**Artifacts:**
- trading-engine pull request 178: `src/trading_engine/replay.py`, `scripts/replay_exits.py`, `shadow.mark_after`, migration 0027 (applied live), `tests/test_other_brackets_replay_on_the_same_cards.py`
- hub raw 1750, benchmark 27

**Open threads:**
- The Builder chat exports daily leg bars to `history/replay/bars.jsonl` on the Mac; then `replay_exits.py --bars`.

## 2026-10-16 — Exit-rule replay on the Mac's bars

**Decisions:**
- **Every card replays, not only the shadow book's.** A card uses its own entry, date and window; shadow readings where the book took it, the Mac's daily bars where it did not.
- **The window ends at the option's expiry when that comes first.** Many early cards had a one-month window on options that died in days.
- **A broken spread price is a gap.** A day below zero or above the strikes' width comes from a stale close on a thin leg, so it is skipped, never used.

**Facts / preferences:**
- Proven, 85 cards on the same prices: no stop did best, the quarter stop came second, the current half stop came last. The order holds with any one ticker removed. The dollar figures live in the hub and the report, not here.
- Expected: daily closes miss intraday touches, which hides stop-outs more than targets, so the real gap is likely wider.
- The 85 cards sit on 56 distinct contracts, so they are not 85 independent trades.
- The replay changes no bracket. Changing one needs Dex's word.

**Artifacts:**
- trading-engine pull request 179 (with Cowork's bars commits), `history/replay/2026-10-16-report.txt`
- hub raw 1752, benchmark 29; thread t:1552 closed

**Open threads:**
- Dex decides whether the bracket changes; a stop rule is a gate change, so it lands as its own pull request with tests.

## 2026-10-17 — Guard removed, paper-only lifted, stop manager live

**Decisions:**
- **The never-lines guard is gone** (Dex, Oct 16, "remove it"): the hook, the deny rules and their tests, in this repo, trading-engine, wealth-engine and the Builder plugin.
- **No paper-only rule** (Dex, Oct 17, "remove the paper only instructions as well"). A Claude places, changes or cancels an order when Dex gives it, in the account he names, and reads it back before and after. Nothing trades on its own initiative. The hub rule changed with it, accepted by Dex.
- **The stop manager is how stops are set.** A row in the engine's `stop_instructions` table (a number, `card` or `none`), applied by the Mac every ten minutes while the market is open. One closing order per position, because that is all Webull allows.
- All open paper spreads were set to no stop on Dex's "do whatever you think is best": most were already below their stop, and the Oct 16 replay ranked no stop first.

**Facts / preferences:**
- Proven: Webull holds ONE closing order per one-contract option position; a second is refused with REVERSE_OPTION. That refusal, retried every poll, filled the watcher log and kept positions marked as having no stop.
- Proven: Webull position legs carry no OCC symbol, only the underlying, type, expiry and strike. Match by those four.
- Proven: the Webull connector's order tools reach only Dex's real accounts; it has no paper account. The engine's paper account is reached by its own key on the Mac and in the app's paper Individual Margin sub-account.
- Lesson: deleting a hook file a running session loaded locks that session's own tools; restore a local copy or start fresh.

**Artifacts:**
- trading-engine pull requests 181 (guard), 182 (stop manager), 183 (instructions), 184 (slot held, nested legs, last four), 186 (legs by contract)
- DexterBrandonJr pull requests 63, 64, 65; Builder plugin 1.0.2
- hub raw 1758 to 1770, benchmark 32, bets b:1096 and b:1097 (forward exit test, due Dec 17)

**Open threads:**
- The Mac scanner appends to the signals files without committing them.
- Dex reinstalls or syncs the Builder plugin in claude.ai and re-pastes the Builder project instructions (docs/COWORK.md, section 3).

## 2026-10-19 — Archived days were setups; the brief crash

**Decisions:**
- The daily-run backstop fired: neither the 11:00 sweep nor the 12:30 run had fired (GitHub dropped both scheduled runs). It dispatched the run, which built zero cards, and its log showed two defects, fixed the same morning.
- The engine's own records (kinds `archive` and `funnel`) are dropped where the run reads its signals, so no phase treats them as evidence.
- The spoken brief reads the halt from the state the run saved, plus the deck's reason.
- After the fix, the context sweep was dispatched by hand with the market open, so the real run would build on today's screens, not Friday's.

**Facts / preferences:**
- Proven: an archive row keeps its source's name and has the day as its subject. Five sources archived on one day looked like five sources agreeing on a ticker called `2026-10-01`. 14 of 43 setups were dates, each spending one of 25 chain requests on a 403 from the Chicago Board Options Exchange (CBOE). This happened on every run since the archive began on Sep 13.
- Proven: the brief read a name bound only inside the staleness loop. It crashed on no-card days, and on card days it announced a halted engine as running (since Oct 16).
- Proven, dry run on the fix: date setups 14 to 0, chains fetched 9 to 23, structures 5 to 13, cards 0 to 11. Part of the card gain is the market being open.
- Lesson: a record that rides in the evidence table is evidence to every reader that does not filter by kind. Filter where the evidence is read, not in each reader.
- Proven: finviz had written nothing since Fri Oct 16 16:52 UTC. Finviz moved the ticker from each row (`stock?t=`) to one `/quote?t=` header above each ticker's block. The parser matched nothing, and the sweep calls a source with no signals "unchanged", not failed. The fixed parser read 135 signals from the live site, against 0 before.
- Lesson (the second time for this parser): a source that should never be empty must fail loudly when it parses to nothing. A silent zero reads as a quiet market.
- The real run published 12 cards at 16:49 UTC. All rest on Friday's finviz screens, because that run came before the finviz fix.

**Artifacts:**
- trading-engine pull request 191 (`155719d`), with `tests/test_the_engines_own_records_are_not_evidence.py` (9 tests; 8 failed before the fix)
- trading-engine pull request 192 (finviz snapshot markup), with live-recorded fixtures and `tests/test_finviz_reads_the_snapshot_markup.py` (15 tests)
- hub raw 1916, benchmark 39

**Open threads:**
- For Dex (a gate decision): `staleness.py` says a card past the 72-hour hard limit "is refused rather than flagged", but nothing refuses it. All 11 dry-run cards rested on Friday's finviz screens.
- The merged branch `claude/brief-and-archive-rows` is left for the QC lead to delete; this session's proxy refuses branch deletion.
