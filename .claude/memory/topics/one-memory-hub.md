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
