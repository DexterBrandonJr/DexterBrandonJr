# One Memory Hub

## 2026-09-25 — Hub design revised under QA/QC after the LLM-Wiki thread

**Decisions:**
- The hub ("one memory, every Claude") is a private Supabase project every surface reads first and writes last: `index`, `facts`, `threads`, `log`, and now `proposals`, with a `brief` view under two thousand words and one boot line in preferences. Design only so far; the build waits on Dex's word.
- Brief 1 was wrong in one place: it applied the forgetting curve to everything. Corrected: every row has a `kind` (rule / fact / thread); only facts age, rules never decay and surface by trigger word. Source: Link 3.0 measured four usage-aware rankings including recency decay and declined all four.
- Contradictions are settled at write time, not read time: a slot is subject + predicate, a new value closes the old row (never deletes it) and points to it. No model is asked "which is current?". Two clocks on every fact: valid time and belief time; the brief prints the date beside each fact.
- Model output is untrusted input: every fact carries a source pointer and a quote, checked deterministically; verified proves the words exist, not that they are true. Unverified facts wear a marker.
- Two write paths: verified facts from owned sources go live; rules, subject merges, guest writes and unverified extractions land in `proposals` for one tap from the morning digest. Capture never blocks; a fallback inbox is reconciled nightly.
- The hub scores itself with its own 25-question probe set (five LongMemEval abilities, exact match on a fact id, Wilson interval, three MemOps-style operation probes) and never quotes a public leaderboard about itself.
- Two smaller rules adopted from the thread: the write path fails loudly rather than storing a placeholder (a stand-in is indistinguishable from a real row once stored), and instructions describe shape, never live values (no counts or ids in the boot line; live values come from the view).
- The `innovation-brief` skill gained a fifth lens (quality control) and two field-scan rules: read the comment thread under the primary source as an adversary, and read a benchmark's audit before its leaderboard.

**Facts / preferences:**
- Dex's ask was for "comprehensive supplementary research … with rigorous QA/QC" against Karpathy's LLM Wiki gist and its thread; he wants counterarguments folded into the design, not a defence of it.
- The LoCoMo audit (Penfield Labs, April 2026): 6.4% of the answer key wrong, the judge accepts 62.8% of intentionally wrong answers; Zep and Mem0 dispute each other's scores on it. Small differences on that benchmark rank nothing.
- memore's measured open problem: the same subject phrased two ways agreed 58% of the time. The alias table is a mitigation, not a solution, and the page says so.
- Hub rows stay Expected until move 1 lands and a green test upgrades each cell.

**Artifacts:**
- Brief 2 of the page "One Memory, Every Claude" (same artifact URL as brief 1), new section 7 with the write-path figure, twelve-lesson table, the field's quality table, the probe set and the unsolved list; twelve new sources.
- `.claude/skills/innovation-brief/references/lenses.md` — the quality-control question bank and the revised field-scan order.

## 2026-09-26 — Built: the hub exists, at stage 2

**Decisions:**
- Dex said build ("begin the building phase … so I can handle it all tomorrow morning"). The hub now lives in the private repo `DexterBrandonJr/one-memory-hub` and the private Supabase project `one-memory-hub`; this file is the pointer. Nothing sensitive here: the project ref, the push topic and the boot line live in the private repo's docs.
- The loop runs inside the database (`pg_cron` nightly, `pg_net` for the push), so it spends no GitHub Actions minutes and needs no machine awake.
- Every Claude Code session on this repo now reads the hub first (see `CLAUDE.md`, "Read the hub first"); the chat-memory files stay the per-repo record.

**Facts / preferences:**
- Build phase done in one sitting: four migrations applied, a twenty-check smoke test passed on the live hub, ten rules and forty-plus verified facts seeded, forty index pointers, eight probes, the nightly job scheduled.
- What only Dex can do is one screen in the private repo (`docs/MORNING.md`): paste the boot line, test from the phone, subscribe to the digest.

**Open threads:**
- The morning list; the chat-search ingest from the phone; the weekly review and the counterfactual are the next increments (tracked in the private repo's build order).
- Cowork transcripts in the data export: still unconfirmed.
- The nightly export of the brief into a private repo through the GitHub contents API (git history as the undo button, no Actions minutes) is an idea, not a decision.

## 2026-09-26 — Every artifact and Code session in; the chat sweep is one phrase

**Decisions:**
- A Code session cannot read claude.ai chats, so the chat sweep runs where the history is: Dex says "sweep my chats" in one phone chat, ten chats a turn, resumable with "continue". The phrase is a hub rule, so every surface knows it; the long paste and its limits are in the private repo (`docs/SWEEP.md`).
- Every artifact and every Claude Code session on the account is indexed in the hub; the details stay in the private hub, not here.
- Dex's Claude Projects write to the hub as trusted authors, like chat and Cowork.

**Facts / preferences:**
- The hub was already in use across surfaces before this session finished: chat, Cowork, a Project and Code all read it first and reported back.
- Two classes the first real traffic found, fixed the same hour: a guard written for one kind of slot did not cover its sibling (duplicate lines from two writers), and a word cap that fixed sections consumed hid most of the record (now one recall call away, and the summary says so). Both are pinned by the hub's smoke test, now 24 checks.

**Artifacts:**
- `.claude/skills/hub/SKILL.md` here carries the new phrases ("sweep my chats", "continue") and the recall step.
- In the private repo: three migrations, `docs/SWEEP.md`, updated boot and morning docs.

**Open threads:**
- Dex runs the sweep from the phone, then once inside each Claude Project.

## 2026-09-26 — Innovations test: guard, watch, ledgers, handoff

**Decisions:**
- Dex asked for an innovations test aimed at autonomy across every device, cybersecurity, and profitability. The finding that shaped everything: a memory every Claude reads is a lethal trifecta by construction (private data, untrusted content, a way out), the attack OWASP calls memory and context poisoning. The defences went in at write time, in code: secrets refused everywhere, provenance, instruction-shaped text held for a human, private subjects never pushed to the phone, and the public API roles locked out.
- A nightly security watch audits the hub's own locks and a register of Dex's accounts (pointers only, never values). Money, unit economics and a scored forecast ledger give each project the three numbers a venture is decided on: burn, margin, break-even. Any device can hand work to Code through the hub.

**Facts / preferences:**
- Three classes were found and fixed within the hour: a lock scoped too narrowly (caught by the new watch in its first minute), the guard refusing honest text (a pattern tuned), and a leak by name in the phone push. The lessons went into the innovation-brief skill's quality-control lens, not only into memory.
- A routine created from a Code session cannot carry connectors on this plan; an autonomous worker that needs a connector is created by Dex in the Claude app.

**Artifacts:**
- The page "Hub Innovations Test" (private artifact); the schema, tests and docs live in the private hub repo.
- `.claude/skills/hub/SKILL.md` here gained the new phrases; `.claude/skills/innovation-brief/references/lenses.md` gained three quality-control questions.

**Open threads:**
- Four taps for Dex, tracked in the private hub: confirm two-factor, create the worker routine, pick the product blanks, settle the first forecasts.

## 2026-09-26 — Shapes, gate and the Mirror (0012–0014)

**Decisions:**
- Building the Hub Kit for strangers produced designs the hub itself
  lacked; Dex asked for both lists built and approved on his behalf. Three
  migrations followed: rules in tiers with an envelope around the brief, a
  paper copy and an export; a self-test any connector can run, a fingerprint
  of the hub's own code that turns an unlogged change into a finding, an
  undo path on every account and key, and an install gate (self-test →
  audit → brief under its cap → integrity); and the Mirror, a private,
  evidence-bound growth profile whose gate lives in code (labels are his to
  state, inferences are capped, only he confirms, the phone push carries
  numbers only).
- The database never pushes its own backup to GitHub: a token in the hub
  would be a secret in the store. Code and the worker write the paper copy.

**Facts / preferences:**
- A reusable testing trick: a throwaway local PostgreSQL with the two
  Supabase extensions stubbed by signature (a job table, a response table)
  applies the real migrations unchanged and runs the self-test before
  anything goes live.
- Two lessons for the working agreement: when the thing being budgeted can
  be rendered, render it instead of estimating (the first live compile
  landed 535 words over); a query alias must never share a name with a
  plpgsql variable.

**Artifacts:**
- Schema, tests, docs and the paper copy live in the private hub repo
  (`DexterBrandonJr/one-memory-hub`). Here: `.claude/skills/hub/SKILL.md`
  gained the gate phrases and a pointer to the private profile's phrases.

**Open threads:**
- The first unattended nightly proves the integrity check and the self-test
  (scored the next morning).

## 2026-09-26 — Routing, a self-writing backlog and a field the hub reads itself

**Decisions:**
- A plain sentence finds its tool. `hub_route(text)` returns the subjects a message touches (whole-word aliases), their open threads, the intents (money, forecast, security, task, feeling, practice, wheel), the profile areas and one `do` row that names what to run; every chat runs it before answering; the words it cannot place feed a nightly learner. Design: the private repo's docs/ROUTING.md.
- The hub writes its own backlog. One row per gap it can measure, four lenses (security, growth, efficiency, reach), three sizes that name who builds (S a chat, M a Code session, L a phased build with a brief first), a score from use and pain, thirteen nightly detectors that upsert by key and mark themselves done when the gap closes. The hub proposes and ranks; it never builds; a guest cannot write it; the push carries counts only. Design: docs/BACKLOG.md there.
- The field. Six public pages (the Claude Code changelog, Anthropic news, the Supabase changelog, Simon Willison's feed, OWASP GenAI, the Hacker News front page for AI) fetched by the hub itself on a cadence and cleaned before the secret guard sees them; a Claude reads the new rows and proposes items that cite their source. The first read produced seven.
- The brief's word cap moved from 3,000 to 3,500, with its revoke path on the record: the fixed sections had left room for 13 facts; at 3,500 the core holds 25. Trimming those sections is on the backlog.

**Facts / preferences:**
- Proven live on 2026-09-26: 70 self-test checks, the install gate 4 of 4, the 29 new functions identical between the files and the live database hash for hash; all six field pages landed clean on the second fetch; the first detector item cleared by the record itself the same afternoon.
- Three failure classes from the first live runs, fixed the same day and recorded: a public page treated as a message (820 KB stored whole, three pages refused as card numbers → a cleaner before the guard); a learner without a stop-list (21 everyday words proposed as aliases for the owner → person subjects and common words skipped); a backreference in a hot regex (32 seconds on a 500 KB page → one pass per tag, 76 ms).
- Nothing here woke Dex: routine approvals in the named window stand, and every decision carries its revoke path.

**Artifacts:**
- Private repo `DexterBrandonJr/one-memory-hub`: migrations `0015_route`, `0016_backlog`, `0016_backlog_field`; docs/ROUTING.md, docs/BACKLOG.md; the worker prompt gained the field, the aliases and the plan; predictions 19–23.
- This repo: `.claude/skills/hub/SKILL.md` (routing and backlog phrases).

**Open threads:**
- The first unattended nightly with the three new steps runs 27 Sep. Dex creates the worker routine in the Claude app so the field, the aliases and the plan run without a chat. From any chat: say `plan`, accept one small item, finish it, say `done`.

## 2026-09-26 — Scenarios live in the hub; the database upgrade checked; model by work

**Decisions:**
- Scenarios is part of the hub (private repo, migration 0017): the same engine as the public skill, run inside the database, with runs and observations kept forever and append-only, forecasts on the hub's ledger, a nightly re-run of stale scenarios, a route intent for plain words ("what if", "which is better", "simulate"), a digest line and a weekly paragraph. No brief section: the brief is at its cap.
- The database upgrade Supabase announced (PostgreSQL 17.6 to 17.11) was checked against the hub's four risk areas: nothing applies, no action needed.
- Model by work: routine chats and Code sessions on Opus 5.5; Fable 5.1 for the brief and the hardest phase of a large build. The hub's backlog names the model per size.

**Facts / preferences:**
- Proven live: self-test 84 checks, gate 4 of 4, the new functions identical live and local; two worked scenarios defined and run with the same answers as the portable engine.
- The daily workers still wait on Dex: a routine made from a Code session cannot carry the database connector on this plan.

**Artifacts:**
- Private repo: `0017_scenarios.sql`, docs/SCENARIOS.md, three failure classes in the working agreement, predictions 24 to 26.
- This repo: `.claude/skills/scenarios/`, the hub skill's what-if row, `CLAUDE.md`.

**Open threads:**
- Dex: log a real workout against the training-day scenario (done or skipped) so the model starts learning from his record; create the worker routine in the Claude app.
