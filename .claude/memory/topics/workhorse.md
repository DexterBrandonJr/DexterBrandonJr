# Workhorse

## 2026-09-11 — How Dex builds, preserved: the workhorse doctrine repo

**Decisions:** Dex asked, after the trading-engine build, for a way to preserve "the main concept of how I prefer things built" so the same posture carries to every project — businesses, finances, digital marketing, firefighting, fitness, art, freelance, anything. It now lives in a dedicated private repo, `DexterBrandonJr/workhorse`: `DOCTRINE.md` (the eight parts of every system — record, gate, loop, surfaces, scorer, review, counterfactual, staged autonomy — the operating rhythm, how to read his requests, the confidence contract, the engineering rules that came from real failures, the surfaces, data and secrets, the response format), `templates/` for a new project (vision, working agreement, build order, QA/QC, memory, CLAUDE.md), `playbooks/domains.md` mapping the eight parts onto each domain, `record/` with the distilled build data from the projects built this way and a registry, and a `workhorse` skill with a scaffold script (`new_project.py`) that lays a new project down from the templates and copies the skill in so the doctrine travels with it.
**Facts / preferences:** The doctrine is edited in place, never appended to as a log; a lesson from a project becomes one rule in its §5, the project's own memory keeps the story. Each project gets its own private repo with its own memory; this public repo stays the coordination point and carries a pointer per project and nothing sensitive. A domain-neutral copy of the skill lives here under `.claude/skills/workhorse/` so any session started from this repo triggers on "build me", "new project", "set this up like trading-engine" and reaches for the full doctrine.
**Artifacts:** `DexterBrandonJr/workhorse` (private, main); `.claude/skills/workhorse/SKILL.md` in this repo; the entry in `CLAUDE.md` under "What lives here".
**Open threads:** The first project scaffolded from the templates will test them for real; anything the templates get wrong is edited in the workhorse repo, not worked around in the project.

## 2026-09-12 — The loop runs on a budget, and the budget has a cliff

**Decisions:** A rule went into the doctrine's §5 rather than being fixed and
forgotten in one project, because it will recur in every private repo built
this way: **a scheduled loop costs money to run, and the account's budget can
be a cliff rather than a slope.** Count the continuous-integration jobs a
project will run per merge on day one, not when the warning email arrives.

**Facts / preferences:**
- **Continuous integration is billed per *job*, rounded up to the whole
  minute.** Job count is the price; compute time is almost irrelevant. A
  seven-job matrix costs seven minutes whether its jobs took twenty seconds
  or four minutes. One project's most recent run finished in 51 seconds of
  wall clock and was billed as seven.
- **A system that commits its own record runs its whole test suite on every
  data commit** unless the paths are excluded. This is not an edge case for
  the way Dex builds: the loop writing its output back to the default branch
  is one of the eight parts, so data commits are *most* of what lands. A
  third of one repo's commits were data-only, each paying the full price to
  prove a JSON file cannot break a Python test.
- **Without a concurrency group, every superseded push runs to completion.**
  Push three times while iterating and all three finish, at full job count,
  when only the newest can tell you anything.
- **A $0 budget set to "stop usage" does not bill — it stops.** That is the
  part worth carrying: when the scheduled loop *is* the product, hitting the
  cap does not produce a small invoice, it takes the product dark until the
  billing month resets. Public repositories are not billed at all, which is
  why coordination and memory work in a public repo is free while the private
  project's loop is not.
- **The diagnosis came from a number that did not fit**, not from an audit:
  the same suite took 14 seconds in one place and 301 in another earlier the
  same day, and chasing that gap is what surfaced a separate defect. A
  measurement that makes no sense is worth an hour.

**Artifacts:** The rule is in `DOCTRINE.md` §5 in the private
`DexterBrandonJr/workhorse` repo. The fix that produced it — path exclusions
for data and documentation commits, and a concurrency group cancelling
superseded pull-request runs — is in the private project repo, and neither
change runs one test fewer.

**Open threads:** The test matrix runs three language versions on every event.
Narrowing that on pull requests and keeping the full matrix on the default
branch is the remaining saving, and it is a coverage decision rather than a
tuning one, so it stays Dex's call.

## 2026-09-12 — An invariant stated as a direction hides the assumption it was built on

**Decisions:** When adding the first instance of a genuinely new case to a
system, go looking for the rules that were written before it existed, rather
than waiting for one to fail. Four separate safety checks in one build all
turned out to state a rule as a *direction* — "must be bought", "stop below
entry", "a stop can only move up", "the entry must be a buy" — when what they
each meant was "the safe way round". Every one of them was correct, and every
one of them inverted on the first case of the new kind. None would have been
found by reading the code looking for bugs, because none was a bug.

**Facts / preferences:** The tell is a rule whose statement names a direction
instead of a property. "Up" is a direction; "reduces exposure" is the
property. Where the two coincided for every case that had ever existed,
nobody had reason to separate them, and the wording quietly became the rule.
When the mirror case arrives, the fix is to restate the property and derive
both directions from it — never to add a branch for the new case, which
leaves the original wording in place to be re-derived wrongly later.

Two related habits proved out on the same build. First, hold that kind of
guarantee as a **property over both directions**, not as one example each: a
mirror is exactly the change that looks correct in all the cases you thought
of. Second, mutate the safe direction and watch the tests fail — the mutation
that silently *widens* a loss is the one worth building the suite around, and
it should fail loudly and in several places.

And the counterweight: not every such rule should be mirrored. One of the
four was the last check before an order reaches the broker, and its stated
purpose was detecting a corrupted payload, not describing the position. Wave
that one through and a real invariant is traded for a feature. Stopping there
and saying so was the right end to the session, not a failure to finish.

**Artifacts:** The specific rules, the mirrored code and the mutation tables
live in the private `trading-engine` repo. Nothing about the instrument or the
accounts belongs here; the pattern is the part worth carrying.

**Open threads:** No way yet to find these rules before they bite — they look
like ordinary correct code and read as confident. Worth a pass over any
module whose docstring states a guarantee in directional language, asking
what property it is standing in for and whether a case exists that would flip
it. That is a search over *wording*, which is unusual and might be the reason
it works.

## 2026-09-13 — A module that exists is not a module that runs

**Decisions:** Before building anything onto a system, check what in it is
actually *called* — by grep, over the working tree, for each module's name
appearing somewhere that is not its own file. Asked "did we build all forty
things", the changelog said yes and was right; the caller list said twelve were
running, seven measured nightly and were never read back, and thirteen had no
caller at all. Every one of those forty passed its tests. A test proves a unit
behaves; only a caller proves it happens.

**Facts / preferences:** The worst case is not the unbuilt thing, it is the
loop that is closed at one end. A nightly job computed measurements for a month
and nothing opened the file, which reads in every log and every summary as a
system that is learning. That failure is invisible from inside each half:
the writer works, the reader works, and nobody owns the join.

Two habits that came out of it. Verify a status claim against the artefact that
would have to be true — a caller, a row in a table, a request in a log — rather
than against the document that records the intention. And when a document
contradicts itself, that contradiction is usually sitting exactly on top of the
real gap: the section saying "wired" and the section saying "not wired" were
both partly true, and the thing neither described was the part that was broken.

Also worth keeping: a browser or integration harness earns its cost the first
time a change breaks the artefact while every unit test stays green. One name
collision in a page produced eleven failures across layout, tap targets and
keyboard handling, none of them near the cause. The fix was a check that runs
first and looks for the cause directly, not more checks on the symptoms.

**Artifacts:** The engine-side counts, the modules and the harness check live in
the private `trading-engine` repo. The ranked build order that came out of the
audit is a published page Dex can reopen.

**Open threads:** No cheap way yet to notice a half-closed loop from the
outside — the write side and the read side are each healthy, and only a person
asking "who reads this" finds it. Worth thinking about whether a module can
declare that it expects a reader, so an unread one is a warning rather than a
silence.

## 2026-09-13 — A module can have a caller while its guard has none

**Decisions:** The previous entry's open thread — "no cheap way yet to notice
a half-closed loop from the outside" — now has an answer, and the answer has
two levels rather than one. A repository scan for **modules nothing imports**
is the cheap check, and it is not sufficient: a module can be imported for one
name while the function that actually guards something is called by nobody.
Both scans now belong in the quality-control pass on any project built this
way, and the second one is the one that found the expensive thing.

**Facts / preferences:**
- **Scan with an abstract-syntax-tree walk, never a regular expression.** A
  regex scan of imports reported sixteen dead modules in one project; four of
  those were reached by *relative* imports (`from .thing import X`) that the
  pattern could not see. The real figure was thirteen. A wrong number here is
  worse than no number: it sends the next session to wire something that was
  never broken, and it went into a published artifact before it was caught.
- **Then scan at function level.** Of 672 public functions in that project, 91
  had no caller outside their own file. Most of that is noise — properties,
  internal helpers — but one was a safety guard that had been written
  correctly and never once run, in the exact area the system had recently
  learned to operate in. The module-level scan could not see it, because the
  module was imported for a different name entirely.
- **The lesson generalises past code.** A capability that is built, correct
  and unreferenced is indistinguishable from one that does not exist, and it
  is *more* dangerous, because everyone involved believes it is there. This
  belongs in the doctrine's engineering rules next to the record and the gate:
  building a thing and wiring a thing are two separate pieces of work, and
  only the second one is delivery.
- **A test suite passing tells you nothing about this.** All 1,961 tests
  passed with thirteen modules dead. Tests prove a module works; they do not
  prove anything runs it. That is what the scans are for.
- **Corollary for the build phases:** the "did it actually execute" question
  belongs in the debug phase as a *scan*, not only as a live run. A live run
  needs credentials and costs continuous-integration minutes; a scan is free
  and catches the whole class in seconds.

**Artifacts:** The two scans (module-level and function-level) as scratch
scripts in the session; worth promoting into the workhorse repo as a
quality-control script so they run on every project rather than being
rewritten each time. The horizon artifact for that project now carries the
corrected count and the correction itself, rather than quietly replacing the
wrong number.

**Open threads:** Promote both scans into `workhorse` as one script, and
decide whether "expects a caller" can be declared by a module so an unwired
one is a warning rather than a silence — the previous entry's question, still
open in its stronger form. Also unresolved: the function-level scan's 91 hits
are mostly noise, so it needs a way to rank a guard above a property before
anyone will run it twice.

## 2026-09-13 — Scanners that read themselves, and the swallow that is not silent

**Decisions:**
- **A quality-control scanner must never scan its own pattern table, and the
  fix is not an exclusion list.** A marker check searched raw lines, so its
  own regex literal — and the docstring sentence explaining the rule — became
  findings. All three of its findings in the whole repository were itself,
  against zero real ones. Excluding the file by name would have blinded it to
  real markers there; reading *comment tokens* instead fixed it without
  blinding anything. Same shape as every other false positive that week:
  **parse the region that matters, do not match a substring in a file.**
- **Deliberately swallowing and silently swallowing are different things, and
  the fix is to carry the reason out, not to raise.** Six handlers swallowed
  on purpose for good reasons (the order is already with the broker; the call
  is outbound only; the fallback is safe). All six now record a reason onto
  the run report, which counts them and prints them. None of them raise. The
  reasons were never the problem — the silence was.
- **When a scanner and a carefully-written module disagree, check the scanner
  first.** The tier flagged the one module written most carefully about that
  exact hazard, because it looked only at the statement immediately after the
  `try` and the module's re-raise was three statements down inside an `if`.

**Facts / preferences:**
- **A tier that cries wolf gets muted, and then catches nothing at all.**
  This is the reason to spend real effort on false positives rather than
  shipping a noisy check and promising to tune it. It is also the reason to
  refuse to ship a half-calibrated new tier.
- **Write the test for the false negative your fix could introduce, not only
  the one for the bug you fixed.** Widening a check to look through a whole
  block risked excusing a swallow because some function defined below raises.
  The test written to pin that failed on the first attempt — the pruning
  guard skipped nested definitions among a node's children but not when the
  statement itself was one. Without that test it would have shipped.
- **A count in prose goes stale the moment the code moves.** A docstring said
  "five places" after six were wired. Same class as the earlier 16-vs-13
  orphan count. If a number describes code, something should derive it.
- **"Called only by its own test" is a distinct orphan class, and a
  reachability scan that counts tests as callers cannot see it.** Measured:
  ~70 public functions, though that number is an overcount until name
  references (a rules tuple, a registry) are handled — the same false
  positive the module-level scan already burned down.

**Artifacts:** The validation protocol merged, then a second pass that took
its own DEFECT findings from nine to zero — six swallows made visible, a
failure journal taught to report its own failure, an over-broad `except`
narrowed to the parse error it meant to catch, a fourteenth orphan wired, and
two corrections to the tiers themselves. Both pull requests are on the
private project repo.

**Open threads:** A fifth tier for "reached only by its own test," calibrated
properly (name references first, then rank a guard above a property) rather
than bolted on. Still open from the previous entry: promote the two
reachability scans into `workhorse` as one script so every project gets them
instead of rewriting them each time.

## 2026-09-13 — A call on the wrong object, and the check that looked one level too high

**Decisions:**
- **Before extending a script, check that what it already does works.** Wiring
  eight dead readings into a scanner started by reading the three it had. Two
  of those three called methods on the wrong object — a vendor library splits
  its client into sub-clients, and the methods lived on siblings of the one
  being called. Both raised `AttributeError` into a broad `except` that logged
  a line and continued, so the run reported an empty market. **Two of its
  three readings had never once worked**, and nothing in the output said so.
- **A surface check has to check the layer that is actually used.** There was
  already a continuous-integration job proving each sub-client exists on the
  vendor client. That is one level too high: it proves the object resolves,
  not that the method called on it does. The new check walks every
  `api.<client>.<method>()` call site and asks the installed library whether
  the name is there. It fired on both and named where each method really
  lives.
- **When a module admits its field names are guesses, do not guess again —
  make the run report what it saw.** The last live run against that vendor
  found every guessed field name wrong but one. So each fetch now returns the
  payload *and the keys the response actually carried*, and a mapping that
  yields nothing prints those keys. An endpoint that returns nothing and an
  endpoint spelled differently are indistinguishable from a row count. One
  real run converts a guess into a committed fact.

**Facts / preferences:**
- **The substring lesson landed on me twice more in one session.** A guard that
  read a whole configuration file failed because my own *comment* named the
  script it forbids — same shape as a scan counting a comment as an import. I
  tightened the guard to read executable content rather than rewording around
  it, with a test that proves it still fires on a real line. Then, triaging
  the wiring tier's findings, I grepped for callers and found four the tier
  said did not exist: every one was prose in a docstring or a string in an
  export list. **The tree walk was right and my grep was wrong.**
- **A tool being present in one job says nothing about another.** A new check
  was added as a step in the job that had the library it needed — and that job
  installed only that library, not the test runner. It went red with "no
  module named pytest", so the check never ran at all. Audit *every* job that
  runs a tool, not just the one that broke.
- **Reproduce a continuous-integration failure before fixing it, even an
  obvious one.** A throwaway virtual environment reproduced the exact message
  in seconds and made the fix verifiable rather than plausible.
- **A table with no reader or writer is the same disease one layer down.** A
  store had existed in a migration for weeks with nothing touching it, so the
  reading that depended on it could never fire however its fields were
  spelled. Finding it took wiring the thing above it.

**Artifacts:** Four pull requests merged on the private project repo: the
multi-tiered validation protocol; a pass taking its own findings from nine
defects to zero; a fifth tier that asks whether a capability is wired or only
tested; and the fetch layer for eight readings that had none — which is what
surfaced the two calls that never resolved.

**Open threads:** Six of the eight readings still carry unverified field
spellings; only a run on the real machine can settle them, and the run is now
built to say which keys it saw. Two things are deliberately off until a human
decides: the futures contract symbols, and an imbalance-side encoding three
live snapshots could not settle. 36 wiring findings remain, none of them
guards.
