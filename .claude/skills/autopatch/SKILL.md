---
name: autopatch
description: Diagnoses real failures a tool recorded while being used, then reproduces, fixes, verifies, and ships them as a reviewable pull request. Trigger this whenever the user reports that one of their own tools is erroring, crashing, or misbehaving; pastes a diagnostic report, error journal, traceback, or selfcheck output; asks to "patch," "fix the bugs," "clean up the errors," or "see what's broken" in a project they built; or wants a tool to watch itself and propose fixes as they use it. Also trigger when setting up that self-monitoring in a new project for the first time.
---

# Autopatch

Turning failures a tool actually hit into merged fixes, without the user having
to diagnose anything.

## The problem this solves

Bugs found by using a tool are worth far more than bugs imagined while building
it — they are real, they are prioritised by frequency, and they come with the
conditions that produced them. But they are also the ones most likely to be
lost: they happen while the user is busy doing something else, and by the time
anyone asks "what went wrong last week?", the answer is gone.

So the loop is: the tool records its own failures as it runs, and this skill
turns that record into patches. The user's attention is required only to review
a pull request.

## The rule that makes this safe

**Never patch what you have not reproduced.** A fix for a bug you inferred from
a traceback is a guess wearing the costume of a fix, and it is worse than no
fix: it consumes review attention, it can mask the real defect, and it makes
the next person believe the problem was handled.

If reproduction fails, say so and stop. "I could not reproduce this" is a
useful, honest report. A speculative patch is not.

## Working a diagnostic report

### 1. Read the report

The standard shape is JSON with an `issues` array, each carrying a stable
`signature`, an `error_type`, a `count`, a `command`, and a `sample_message`.
`scripts/triage.py` will parse and rank one for you:

```bash
csearch selfcheck --json > /tmp/report.json          # or the tool's equivalent
python3 .claude/skills/autopatch/scripts/triage.py /tmp/report.json
```

Work in the order it gives you: frequency first. The issue hit thirty times is
worth an afternoon; the one hit once may be worth nothing at all.

Note what the report does *not* contain. Reports are usually redacted — file
paths reduced to shape — because they may be shared. If you genuinely need the
real paths, ask the user to re-run without redaction locally rather than
guessing at what was elided.

### 2. Reproduce it as a failing test

Before touching the implementation, write a test that fails for the reason the
report describes. This is the step that separates a fix from a guess, and it
has a second payoff: the test is the regression guard, so the bug cannot come
back silently.

If you cannot make it fail, you do not yet understand the bug. Keep
investigating, or report that you could not reproduce it — do not proceed to a
patch.

### 3. Fix the root cause, not the symptom

The traceback shows where the program noticed the problem, which is rarely
where the problem is. A `KeyError` at the point of use usually means something
upstream failed to populate a value; catching the `KeyError` hides the defect
rather than removing it.

Ask what invariant was broken and restore it there.

Keep each fix minimal and scoped to the issue. A patch that also refactors
neighbouring code is much harder to review and much easier to get wrong.

### 4. Verify

Run the project's full test suite, not just the new test. Then re-run whatever
originally failed and confirm it now succeeds. A fix that passes tests but
leaves the real command broken has not been verified.

### 5. Ship it as a reviewable pull request

One branch, one draft pull request. In the description, for each issue: the
signature, what actually caused it, what changed, and how it was verified.
Reference signatures explicitly so the user can match them to what they saw.

Never merge. The user reviews.

### 6. Close the loop

Once merged and the fix is confirmed in use, the recorded occurrences are
history rather than an open problem — `csearch selfcheck --clear` (or the
tool's equivalent) resets the record. Do this only after a fix is confirmed
working, never to make a report look clean.

## Instrumenting a new project

To give another tool the same self-reporting, it needs three things. The
reference implementation is `src/csearch/journal.py` in
`DexterBrandonJr/macos-contextual-search` — copy its shape rather than
reinventing it.

1. **A journal.** Newline-delimited JSON, appended to on every run, in the
   tool's own data directory. One line per run; failures additionally record
   `error_type`, `error_message`, and a `signature`.

   The signature is the important part: a hash of the exception type plus the
   function names in the traceback, **excluding line numbers and the message**.
   Line numbers shift when unrelated code is edited, and messages usually embed
   a value that differs every time — including either would make one unfixed
   bug look like dozens of new ones.

2. **A report command.** `<tool> selfcheck`, with `--json` for machines,
   `--brief` for a hook (silent when healthy), and redaction on by default so
   the output can be pasted somewhere without leaking file paths.

3. **A `SessionStart` hook** in the project's `.claude/settings.json`, running
   the brief form. That is what makes it continuous rather than something the
   user has to remember. It must be silent when healthy and must never fail the
   session — see `references/instrumenting.md` for the full checklist.

## What not to do

- Do not patch a bug you could not reproduce.
- Do not widen a patch beyond the issue it addresses.
- Do not disable, skip, or loosen a test to make a suite pass. A failing test
  after your change means the change is wrong, or the test is — investigate
  which, and say so.
- Do not clear a journal to make a report look healthy.
- Do not merge your own pull request.
- Do not treat a low-count issue as urgent because it is recent, or a
  high-count one as trivial because it is familiar.
