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
