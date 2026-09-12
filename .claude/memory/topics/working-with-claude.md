# Working With Claude

*An editable document — edit it in place rather than appending corrections
underneath.*

## 2026-09-11 — The confidence contract

**Decisions:** How Claude carries confidence, and how that confidence earns
trust, is now written down rather than left to tone. Three tiers, never
blurred:

| Tier | What it means |
|---|---|
| **Proven** | It happened, in the real system, and was observed |
| **Tested** | Asserted in code; the real behaviour has not been seen yet |
| **Expected** | Reasoning, with no evidence behind it yet |

Confidence does not become trustworthy by being expressed more forcefully. It
becomes trustworthy when the tiers are never wrong — so "Proven" has to stay
the strongest word available, which means never spending it on anything less.
The corollary carries equal weight: **do not hedge what is actually known.**
Hedging everything makes the strong claims unreadable and is its own quiet
dishonesty.

The pattern this exists to prevent, learned the expensive way on a build
project: *a report outrunning the truth.* A call returning 200 does not mean
the thing it created survived; a guard that did not raise does not mean the
guard checked anything; a function returning a dictionary does not mean the
real-world effect landed. Each of those was an **Expected** reported as
**Proven**, and none was a failure of the machinery underneath.

**How trust compounds, day by day:**
- **One deposit per session** — move at least one thing up a tier and name it.
- **Predictions go on the record before the outcome**, then get scored, so
  confidence becomes a number that can be quoted back rather than a mood.
- **Close every loop opened.** An open thread that quietly dies teaches that
  open threads don't mean anything.
- **Deliver, then ask.** Ask only where the answer changes what gets built.
- **Report against the plan**, so progress lands on a map that already exists.

**The failure protocol:** say it in one line at the top, fix it in the same
response, record the *class* of mistake rather than the incident, and move on.
No apology paragraphs and no tallying of past errors — rumination reads as
instability, which erodes confidence more than the original error did.

**Facts / preferences:** Standing response format across all projects: lead
with what changed, not with what is about to be done; sectioned detail in the
middle; **end every response with a short, plain-language summary** — short
lines, the payload at the bottom, because that is where it gets read. Spell
out and explain acronyms on first use (a long-standing preference, already its
own topic). Pull requests referenced as full markdown links, never a bare
number. Never a wall of options — recommend one and name the runner-up in a
clause.

Two reading habits that prevent the most rework:
- **A directional instruction is a vector, not a specification.** "At least X,
  ideally more" sets a floor and a direction. Turning it into a single hard
  number, and presenting that number as if it came from the user, is the
  specific failure. Pick a number when one is needed — and say out loud that
  it was picked.
- **An analogy names a discipline to import, never an identity to imitate.**
  "How would a major institution approach this?" asks which habits transfer to
  the situation at hand; it does not ask for an impression of one.

## Green here is not green there — 2026-09-12

A suite passing locally is evidence about *this container*, not about the
project. Two test files imported `pyyaml`; the package's `dev` extra never
declared it. Locally it was installed, so the suite went green and the
result was reported as green. On the runner, collection died.

Three things make this worth keeping rather than filing as a typo:

- **The failure mode was silence, not noise.** `1 skipped, 2 errors` is not
  two broken tests — two *collection* errors stop pytest before anything
  runs. The whole suite had not executed on the last two merges, so every
  safety guard in the project was unverified while being reported as
  verified.
- **It was found by an unrelated event.** A red check on a later, separate
  branch. Nothing about the merges themselves surfaced it, because the thing
  that would have surfaced it was the thing that was broken.
- **The fix is cheap; the verification habit is the point.** The repair took
  one line. Proving it took a clean virtual environment, an install from the
  declared extras only, and a collect — reproducing the *runner's* conditions
  rather than trusting this machine's.

**The rule:** when a result depends on the environment — a dependency, a
path, a binary, an installed tool — verify it in an environment built the way
the real one is built, not in the one that happens to be to hand. And when
reporting a suite as green, say which environment it was green in.

## A guessed interface is not a built feature — 2026-09-12

Thirty-odd modules were built fast and deliberately untested, on Dex's
explicit instruction, with testing and debugging as later phases he would
start. That worked, and it is worth recording what each phase actually cost,
because the split is a reusable way to work rather than a one-off.

**The build phase produced working shapes and wrong numbers.** Every module
compiled, imported and read correctly. What it could not produce was any
contact with reality.

**The test phase found three real bugs in a day's work**, all of the kind
that survives a read-through because the code looks like it does the right
thing: a cap that refused the very first item it was meant to govern, a decay
curve that reported *total* decay as *no* decay because the log of zero is
undefined, and a scorer that rated a source which never changes its mind as
maximally trustworthy.

**The debug phase found the expensive ones.** Reading the live interface
rather than its documentation showed that essentially every field name guessed
during the build was wrong — and more importantly, that two *thresholds* were
wrong by an order of magnitude in the direction that silences a feature
completely. The single most valuable finding was that the highest-ranked item
in the whole plan would have produced nothing, ever, and nothing in the code,
the tests or the review would have said so. Only real data said so.

**The transferable rules:**

- **A threshold guessed without data is a coin flip on whether a feature
  exists at all.** Calibrate against real samples and record the samples in
  the code next to the number.
- **When an encoding is ambiguous, record and do not claim.** An undocumented
  integer that might mean the opposite of what you assume makes a feature
  confidently wrong half the time, which is worse than absent. Store the raw
  value, emit no claim, and leave one switch to flip once the record settles
  it.
- **Some corrections are structural, not textual.** An endpoint that returns
  only a current value cannot support a "change since yesterday" feature
  however the fields are spelled — that needs storage, which is a schema
  change discovered only by looking.
- **Build fast, then test, then debug is a real sequence** — but it is only
  honest if the untested work is kept where it cannot run. A branch is what
  makes "testing is a later phase" true rather than aspirational.

**Artifacts:** The full version of this — including the personal context that
shapes it and the project-specific history behind each lesson — lives in the
private `DexterBrandonJr/trading-engine` repository at
`.claude/memory/topics/working-with-dex.md`. That is the canonical document;
this entry carries only the parts that are general and safe to keep in a
public repository. Its companion, `docs/VISION.md` in the same private repo,
covers what that system is meant to become.

**Open threads:** The prediction ledger described above has no entries yet —
it starts the first time a prediction is written down before its outcome is
known.

## 2026-09-12 — Verifying a UI fix: two overflow bugs, two tests

**Decisions:** "Text runs off the page" and "content spills outside its
element" are **two different bugs and need two different tests.** A
page-level check — does the document scroll sideways — is structurally blind
to the second one: whenever any ancestor has `overflow: hidden`, the content
is clipped rather than pushed out, so the page never widens and the test
stays green while the user is still looking at a word cut in half. The
second test is a different question asked of every element: is
`scrollWidth > clientWidth`, excluding the containers that are meant to
scroll. Both now run at 320 / 360 / 390 / 430 / 768 / 1024 / 1440 px.

**Facts / preferences:**
- **Run a new test against the broken version first.** A test that has never
  failed has proved nothing. Running the page-level check against the old
  build reproduced the reported bug exactly — a 439 px page inside a 320 px
  phone — which is what made the later pass mean something. Do this before
  reporting a fix, not after.
- **Text overflow is usually not about length — it is about breakability.**
  Long prose wraps by itself. What breaks a layout is a single unbreakable
  token: a file path, a shell command, an option symbol, a hex fingerprint, a
  URL. The fix is `overflow-wrap: anywhere` on the containers that hold
  identifiers, plus `min-width: 0` on flex and grid children, whose default
  `auto` minimum silently refuses to shrink below their content.
- **A flex item shrinks below its own content by default.** That is how a
  button ended up narrower than the word inside it, with the text spilling
  past its own border. Controls in a flex row want `flex: 0 0 auto`; the text
  beside them is what should give way.
- **A media query placed above the rule it means to override silently
  loses.** Same specificity, so source order decides. The failure is nastier
  than a rule that does nothing: only the properties the base rule does *not*
  also set survive, so the block looks partly applied rather than dead, and
  it can sit wrong for months. Wide-screen overrides belong *after* the
  narrow-screen base, not with the rest of the layout above it.
- **Look at the render after the tests are green.** Both of the day's worst
  findings — a desktop navigation rail stretched into a ladder of empty
  blocks, and the clipped button above — were found in a screenshot, with
  every automated check passing. Screenshots at one phone width and one
  desktop width are cheap and catch a class the assertions cannot express.
- **An invisible tap target needs its own proof.** Widening a control with an
  absolutely positioned pseudo-element works only if no ancestor clips it,
  and nothing about the appearance tells you either way. `elementFromPoint`
  just outside the visible edge answers it in one call.

**Artifacts:** The deck was republished with these fixes; the tests written
for it (`overflowtest.mjs`, `selfoverflow.mjs`, `switchtap.mjs`, `keynav.mjs`)
are scratch files, not committed — the durable part is the reasoning above,
which is why it is recorded here rather than as code.

**Open threads:** The two overflow tests are throwaway scripts run by hand.
Nothing re-runs them when the page changes, so the next edit can reintroduce
either bug class silently. Worth making them a checked-in step for any page
that gets iterated on.
