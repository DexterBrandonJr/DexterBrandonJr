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

**Open threads:**
- Move 1 of the hub (schema with the write path, the brief view, the boot line) starts on Dex's "build". The hub gets its own private repo; this file is the pointer.
- Cowork transcripts in the data export: still unconfirmed.
- The nightly export of the brief into a private repo through the GitHub contents API (git history as the undo button, no Actions minutes) is an idea, not a decision.
