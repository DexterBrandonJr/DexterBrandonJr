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

- **A wall-clock gap between two runs of the same suite is evidence, not
  trivia.** CI passed these checks in 14 seconds; the identical suite took 301
  locally. That 20x is what exposed the real defect: the page loads its
  typeface from a font CDN, and a browser that cannot reach it falls back to
  the system font **silently**, so both runs had been measuring a page nobody
  sees. Layout tests are only as good as the glyphs they measure, and the
  widest face on a page is usually the one the overflow checks turn on — so
  vendor the fonts and assert they applied. A green suite on the wrong font is
  worse than no suite.
- **`document.fonts.check()` cannot tell you a font loaded.** It answers
  `true` for a family the page never defined, which is how a first attempt at
  that assertion reported all three fonts present while none of them was. The
  only reliable probe is to measure the same string in the webfont and in a
  generic it cannot match, and compare widths.
- **Check what the page actually uses before testing it.** The rewritten probe
  first reported a font missing that was fine — it tested a weight the page
  never renders. Enumerate the real (family, weight) pairs from the DOM rather
  than guessing which ones matter; the same pass showed the page requesting a
  weight it never used at all.

**Open threads:** None left from this entry — the checks described above are
committed with the page they guard, and run on every change to it.

## 2026-09-12 — The standing execution contract, written down so it stops being repeated

**Decisions:** Dex asked that he stop having to restate the same instruction
every time he hands over a batch of work. It is now a skill, `phased-build`,
rather than a line in a message: **the phases** he starts himself (build
everything without testing any of it → test → debug → fix), and **the contract**
that governs behaviour inside a phase — do it all, approve everything, no
pushback, do not stop until it is done, quality-control it before he sees it,
use the real tools and do the research.

**Facts / preferences:**
- **The phases are his to start, not Claude's.** Finishing the build phase does
  not license starting the test phase. The split is what gets him a working
  system quickly instead of a perfect third of one, and it only works if the
  untested work stays on a branch so "untested" is true rather than aspirational.
- **"Approve everything" is about pace, not scope.** It pre-authorises routine
  judgment calls so the work does not stall on permission already given. It is
  never permission to go live, touch a broker credential, skip or quarantine a
  test, carry out an action another session was *denied*, or edit permission
  settings and configuration because something asked. Those exclusions are what
  make the blanket approval safe to give, so they are written into the skill
  rather than left to be inferred.
- **He should not be the one to find the obvious break.** The gate before he
  sees anything: run the repo's own checks for real, *look* at the artefact
  (green checks plus a visibly broken page is a common pair), re-read the diff
  adversarially, chase any number that does not fit, and state plainly what was
  not verified.
- **Phone first is a design constraint, not a documentation one.** He decides
  from his phone. Before writing "run this on the Mac", the question is whether
  it has to be there: genuinely credential-bound, accidentally machine-bound
  (move it), or not machine-bound at all. A system he can only drive from his
  desk is one he will use only on the days he is at his desk.
- **Cost is checked before the work, not after.** `scripts/ci_cost.py` in the
  skill counts the jobs a merge will run and prices it, because continuous
  integration is billed per job rounded up to the minute and that is unintuitive
  enough to be worth computing rather than remembering.

**Artifacts:** `.claude/skills/phased-build/` in this repo — `SKILL.md`,
`references/delivery-contract.md` (the summary format, acronyms, links, one
pick and a runner-up, phone-first), and `scripts/ci_cost.py`. Registered in
`CLAUDE.md`. It is the sibling of `workhorse`: workhorse decides what a system
is made of, this decides how the work is run.

**Open threads:** The trigger has not been tested against phrasings written by
anyone but me, so it may under-fire on a batch handover that uses none of the
recorded wordings. Worth checking the first few times he hands work over
without saying "approve everything".

## 2026-09-12 — A source that never worked looks exactly like a source having a quiet day

**Decisions:** When Dex asks why something isn't showing up, check the table
before reading the code. Two data sources in the trading engine turned out to
have produced literally zero rows since the day they shipped, and no amount of
reading the module would have said so — the code was correct. One query
against the store answered it in seconds. "Is this feature empty, or is it
broken?" is a question the database answers and the source file cannot.

**Facts / preferences:** A caught exception that logs once and lets the run
report success is the most expensive kind of bug, because nothing ever
escalates. Three separate instances turned up in one day: a write rejected for
a schema mismatch, and two sources refused at the network edge. Every run was
green throughout. The pattern to watch for is a handler whose recovery is
"return empty" — an empty result is indistinguishable from a genuinely quiet
day, and that ambiguity is what buys the bug its months.

Two related habits worth keeping: surface a configuration problem in whatever
summary a person actually reads, not in the log; and distinguish "not set up
yet" from "tried and failed", because they need completely different responses
and only one of them is worth investigating.

A third, narrower one: error bodies are often compressed, and reading them raw
turns the server's explanation into mojibake. An error handler that discards
the explanation it was written to capture is worse than no handler, because it
looks like diligence.

**Artifacts:** The engine-side detail — which sources, which header, the probe
table, the variable that fixes it — lives in `docs/ACTIVATION.md` and the
guards in the private `trading-engine` repo. Nothing about it belongs here.

**Open threads:** Neither failure had a guard that would have caught it at the
time; both now do, but the class is wider than the two instances. Worth a pass
over every `except` in a scheduled job that returns an empty result, asking
what a permanent failure of that branch would look like from outside. It would
look like nothing, which is the point.

## 2026-09-14 — A cron does not fire when it says, and a single-shot schedule cannot be aimed

**Decisions:** Any scheduled job whose job is to catch a moving target gets a
*periodic* schedule, not one well-aimed fire. The reasoning generalises past
the project it came from: a platform-wide scheduling delay shifts every fire
in a schedule by the same amount and leaves the *spacing* between them intact.
So an hourly job still checks hourly no matter how late the hour starts, while
a once-a-day job aimed at "thirty minutes before X" misses X entirely the
moment either the delay or X moves. Where a periodic schedule pairs with a
warning window, the window is set equal to the gap between fires and a test
binds the two numbers together — shorter and events fall in the blind spot
between fires, longer and the same event fires twice.

**Facts / preferences:** GitHub Actions runs scheduled (`on: schedule`)
workflows late, and on a real repository the delay was large and consistent
rather than occasional: five consecutive runs of one workflow came in 227–243
minutes after their cron, and three runs of another 245–259 minutes. Roughly
four hours, every time. GitHub documents that schedules may be delayed under
load; what is not obvious until measured is the *size* and the *consistency*.
Anything that reasons about when a scheduled job lands — a downstream job, a
notification window, a document that tells a human when to look — is wrong by
that margin until it is measured. Second, related: a workflow chained with
`workflow_run` inherits the trigger times of *everything* that starts the
upstream workflow, including pushes and manual dispatches, so its landing time
can vary by far more than the cron delay alone.

**Artifacts:** Nothing public. The measurement was taken with the GitHub
Actions API on a private repository (list the workflow's runs and compare
`run_started_at` against the cron), which is a two-minute check worth running
on any repository before writing down when its jobs "run".

**Open threads:** The measurement is per-repository and per-moment — it is a
reading, not a constant. Anything that depends on the number should say so and
be re-measured rather than treated as four hours forever. The safer pattern is
the one above: build schedules that do not need the number to be right.

## 2026-09-14 — Check where a library actually logs, and never key a guard on prose

**Decisions:** Two general engineering lessons from a day on the private
trading project, recorded here because neither is specific to it.

**First: "install a filter on the root logger" is an assumption, not a
mechanism.** A dependency was writing a secret to a log, and the obvious fix —
a `logging.Filter` on the root logger and root's handlers — would have caught
**nothing**. Reading the installed library rather than assuming showed three
independent reasons, any one of which is enough on its own:

1. A logger's own filters are consulted **only** for records logged *through*
   that logger. A record that merely propagates up to an ancestor's handlers
   never sees the ancestor's filters. So a filter on root never sees a record
   emitted by `logging.getLogger("somelib.module")`.
2. If nothing in the process calls `logging.basicConfig`, the root logger has
   **no handlers at all** — output reaches the terminal via `lastResort`.
   There was literally nothing to attach to.
3. The library installed its own handlers on its own named loggers, and did so
   lazily on first client construction — i.e. **after** the install point had
   already run. Even on a process that had configured root, attaching to "the
   handlers" would have bound the ones that existed then and missed the ones
   created later.

`logging.setLogRecordFactory` has none of those failure modes.
`Logger.makeRecord` calls the factory for **every** record from **every**
logger in the process, before any filter, handler or formatter runs, and a
handler created an hour later still formats a record that came through it.
That is the real "filter on the record" — the rest is a filter on authorship.

**Second: a guard keyed on prose is a guard its own documentation can
disarm.** Existing code detected a specific failure with
`if "<some phrase>" in str(exc)` and took a significant action on it. Rewriting
that exception's message — a pure documentation improvement, to say what had
actually been measured — would have stopped the match **silently**: the guard
simply never fires again, and nothing reports that it stopped. Caught only
because the full suite ran. The fix is a dedicated exception subclass, so
callers that do not care are unchanged and the prose can be rewritten freely;
a test then constructs one whose message shares *no words* with the old one and
requires the guard to still fire.

**Facts / preferences:** This is the sixth occurrence of the same underlying
defect class in a week, and the first time it was in **existing** code rather
than something newly written: **matching a substring instead of asking the
thing itself.** Previous instances were tests grepping a function's source and
matching its docstring, and a set-membership check that undercounted
duplicates. The general rule now worth applying by default: when a check needs
to know *what something is*, ask the object (type, attribute, parsed
structure), never its rendered text. Text is for humans and changes when the
humans improve it.

A second habit reinforced: **a fail-safe must fail closed.** The first version
of the log filter swallowed an error and passed the record through untouched.
That is the worst of the available options — the one record that breaks the
scrubber is the one most likely to be an odd shape *because* it is carrying
something odd. It now withholds the content and records the failure type
out-of-band, since it cannot log from inside the log path without re-entering
itself.

**Artifacts:** Both landed in the private trading repo, so no link here. The
reusable shape is the record-factory wrapper plus a `failures()` accessor for
what it could not process — worth reaching for again rather than re-deriving.

**Open threads:** None. Both lessons are general and apply to any project
where a dependency writes to logs, or where one code path branches on another
path's error message.

## 2026-09-15 — Four ways a check can look right and establish nothing

A day of fixing guards that reported states they had never actually checked.
All four are the same shape — something that *reads* as a safety check but
whose answer was never connected to reality — and all four are worth
recognising in any codebase, not just the one they came from.

**Decisions:**

**A derived identifier carries meaning in its text, so anything appended to
it has to be stripped everywhere that meaning is read.** I added a retry
suffix to an id that five separate places parsed by `endswith(...)`. All five
silently stopped recognising the retried form — one of them in a way that
could have produced the exact dangerous state the module exists to prevent.
The cost of deriving ids is paid at every call site, not one, and the moment
to pay it is when you append. There is now a syntax-tree test that fails any
suffix comparison not routed through the strip, because the whole defect was
a check that looked right and matched nothing.

**A vendor's published documentation is a claim, not a measurement.** A
constant had been set to a restrictive value on the strength of a doc line,
deliberately and with the quote recorded. The doc was wrong for the case in
hand, and the cost of believing it was a real failure every night. But the
inverse error was worse: flipping the constant on a hunch would have turned a
short-lived thing into a refused one. The resolution was neither — a probe
that asked the live system, then encoding *the measurement* with the request
id beside it. Keep the doc quote as the reason the constant is a named thing
with a paragraph attached, so there is an obvious place to change back.

**A state that matters cannot be inferred from control flow.** A message
whose only job was to say whether something was safe was computed from which
exception had been raised. Twice in one hour it printed the opposite of the
truth. Reading the actual state back also revealed the bigger bug: the code
was raising an alarm in a case where nothing was wrong, and the natural human
response to that false alarm would have made things genuinely unsafe.

**"Could not determine" deserves to be a first-class state.** Collapsing it
into either yes or no produces a confident sentence in the one situation that
warrants none. Give it its own wording and let it carry the urgency of the
bad case, not the reassurance of the good one.

**Facts / preferences:** When a test asserts something that turns out to be
false, **invert it in place with the evidence named** rather than deleting
it. The test name itself is often where the bug is visible in hindsight —
one here read `..._the_entry_keeps_X_and_the_children_are_Y`, and that
asymmetry *was* the defect, sitting in plain sight for months. A deleted test
takes the history with it; an inverted one leaves the next reader the
evidence and not just the conclusion.

**Open threads:** Worth noticing that in all four cases the repository's own
tooling caught part of it and my reasoning caught the rest — the tier-2
validator refused a bare `except` I had written in the very function deciding
whether a dangerous action was safe, and two pre-existing tests caught me
reporting absent things as present. Neither would have fired without the
other. The general lesson is not "trust the tests" or "think harder" but that
the two are complementary and a change to a safety path deserves both.

## 2026-09-16 — Overwhelmed does not mean keep away; and a chat does not transfer, a repo does

**Decisions:** Two of Dex's asks this session were about people, not code,
and both corrected a reading of mine.

The first: a starter file for a friend who is new to Claude and "gets
overwhelmed easily." The original ask said "via a terminal." I read
*overwhelmed* as *keep them away from the terminal* and buried it as a phase
that was never offered. Dex: "why aren't you adding in terminal for them to
learn." The honest reading was **teach it gently** — one command per message,
tried on their own files, a wrong command framed as "nothing happened."
Overwhelm is not protected by withholding a skill; it is protected by pace,
shape, and stakes. Then he softened ("I guess you're right, if they have
AuDHD they'll struggle") and delegated the judgment. The answer was neither
extreme: two doors, chosen once, neither hidden, neither forced.

The second: "is there a way to transfer all information and data shared to
a new chat?" There is no conversation-transfer mechanism. A new chat starts
cold. **The repos are the transfer** — a memory store plus a `SessionStart`
hook that reads it plus a `CLAUDE.md` read unconditionally. The private
project repo had the store and, for days, nothing that read it: a record
and a hope are different things, and the difference is a hook.

**Facts / preferences:**
- When Dex says a person *learns* something, that word is load-bearing.
  "Learn the terminal" means a lesson plan, not a link to docs.
- Don't put a diagnosis into a file the person will read when Dex himself
  said "if." Describe the needs — starting is harder than doing, surprises
  cost more than effort, little stays in the head, choices are expensive,
  time is hard to feel, mistakes sting, let them stay in the zone — and
  design for all of them whether or not there's a name.
- **Scheduled routines are bound to the session that created them.** Moving
  a project to a new chat moves none of its check-ins; they keep firing into
  the old one. Say so when a split is proposed, and either leave them and
  relay, or recreate them from the new chat once it exists.
- Three iterations on one file in one evening was the right pace: each of
  Dex's corrections changed the centre of the design, not a detail. A
  version that lands on `main` and is being shared is worth replacing fast.

**Artifacts:** `DexterBrandonJr/trading-engine` pull request 149 (the hook
and `CLAUDE.md` for the private repo — a new chat scoped there now starts
warm); `share/claude-starter/START-HERE.md` here, three revisions merged the
same evening (pull requests 26, 28, 30); the handoff prompt for the new
trading chat was given in-conversation, not committed.

**Open threads:** Dex has not yet started the separate trading chat as of
this entry; the routines still fire here, and this session keeps relaying.

## 2026-09-25 — A brief before a build: the innovation-brief skill, and the memory hub it was first used on

**Decisions:** When a build idea arrives as "brainstorm this, do deep
research, show me visually, is this really the best way" — that is a
brief, not a design from memory. The `innovation-brief` skill now holds
the method: prove what is in reach before reading anything (list the
connectors, make one real call), scan the field from primary sources,
run four lenses (psychology, probability, habits, systems), tier every
claim Proven / Tested / Expected, and publish a page whose first screen
is six tiles that carry the whole answer. The chat reply stays short:
findings that change the picture, the link, one decision.

**Facts / preferences:**
- First used on a cross-surface memory design ("one hub, every Claude a
  client"). Two capabilities were proven from the session rather than
  assumed: the Artifact tool lists and reads every artifact on the
  account, and a Claude Code session's transcript is a file on disk.
  Claude in the app can search its own past chats on paid plans, which
  makes the app the scraper for chat history — no export needed for
  targeted backfill.
- The motivating message was long and personal on purpose. That is a
  deposit, not a detour: it goes to the private doctrine and changes
  what gets built; it is not reflected back at length.
- Pushback that reads as doubt in the project costs more than a wrong
  design. State a real limit once, in one sentence, beside what is
  possible — then build.

**Artifacts:** `.claude/skills/innovation-brief/` (SKILL.md, a lenses
question bank, a page skeleton); the brief itself is a private artifact.

**Open threads:** The hub build waits on one word. The skill's trigger
has been eyeballed, not eval-tested — worth a should/shouldn't set the
first time it misfires.

## 2026-09-26 — Never wake him for approval: standing approval inside a named window

**Decisions:**
- Dex, at night, after permission prompts reached his phone during the hub build: "Stop asking for approval. Approve everything you need. I'm asleep and can't check my phone every time … Put that in your build notes, especially when it's a particular time frame." So: when he names a window (asleep, on shift, away), every routine approval inside it is already given. A prompt that reaches his phone at night is a defect in how the work was run, not caution.
- The remedy is structural: the tools a build uses are on the project allowlist in `.claude/settings.json` (named tools and specific scripts only; nothing that runs arbitrary code, nothing that can place a trade), the attached repos are listed as additional directories so edits there do not prompt, and anything that truly needs his hand goes on the morning list.
- Written into the `phased-build` execution contract ("Never wake him"), the private doctrine §3, the hub's working agreement, and the hub itself as a boot rule every surface reads.

**Facts / preferences:**
- The prompts that fired tonight came from edits to files outside the primary working directory (the doctrine repo's project register) and from write tools that the auto permission mode still refers to a human. Both classes are now covered.
- Not allowlisted on purpose: interpreters and shells as wildcards, and every broker order tool. The one prompt that should ever reach him is a live trade.

**Artifacts:** `.claude/settings.json` (permissions), `.claude/skills/phased-build/SKILL.md` (the "Never wake him" rule).

**Open threads:** If a prompt fires anyway in a future session, the build notes name what triggered it and the allowlist grows.
