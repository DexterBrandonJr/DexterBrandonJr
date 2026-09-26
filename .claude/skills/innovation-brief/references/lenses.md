# The lenses — question bank

Run all four. Skip a question only when it plainly does not apply, and say so on the page rather than silently.

## Psychology

Named effects to test each design piece against. Cite the researcher; never invent a percentage.

| Effect | Ask | Typical place in a design |
|---|---|---|
| Extended mind (Clark & Chalmers, 1998) | Is the external store consulted reliably enough to count as memory? | The rule that every session reads it first |
| Transactive memory (Wegner) | Does the system know *where* things are, or try to hold everything? | An index table; pointers over copies |
| Zeigarnik effect | Where do open loops go so the head can drop them? | A threads table with owner and next step |
| Cue-dependent recall (Tulving) | Is the retrieval cue the same every time? | One boot line, identical on every surface |
| Working-memory load | What must be held in the head while doing the task? | A small core loaded first; size cap stated |
| Implementation intentions (Gollwitzer) | Is the habit "when X, I do Y", with X concrete? | "When a chat ends, say *log this*" |
| Spacing effect / forgetting curve (Ebbinghaus) | What decays, what is re-touched, on what schedule? | A nightly pass that re-surfaces and prunes |
| Loss aversion / sunk cost | Which framing keeps him from abandoning it after a bad week? | Milestones named plainly; one number he can quote |

## Probability and statistics

- Write the cost as an expected value: `E[cost] = p(miss) × c(re-explain)`. Name both variables and say what drives each down.
- Give one illustrative number, labeled illustrative, and name the measured number that replaces it (a hit rate, a count of misses, minutes saved).
- Prefer a curve drawn to scale over an adjective: if the argument is decay, plot the decay from its formula.
- Base rates: what fraction of systems like this are abandoned in the first month, and which design choice addresses that? (Most personal knowledge systems die of capture friction, not storage.)
- Bayesian pruning: a fact's stability rises with each use; a fact never used loses its place in the core. Say the rule.

## Habits

- One cue, one routine. Name both. If the routine needs willpower, redesign the cue.
- The minimum viable capture is one line typed on a phone. Anything longer will not happen on shift.
- Same message shape every time; the reader should know where to look before reading.
- The system must produce value on day one with zero backlog processed; backfill is a bonus, never a prerequisite.

## Systems — the eight parts, derived

For each, one sentence naming the concrete thing in this build. A blank is a finding.

| Part | This build's answer |
|---|---|
| The record | |
| The gate | |
| The loop | |
| The surfaces | |
| The scorer | |
| The review | |
| The counterfactual | |
| Staged autonomy | |

## Quality control — the fifth lens

Run it after the other four, as an adversary of the draft. Every "yes" needs the mechanism named on the page; every "no" is a finding, not a gap to hide. A brief with no "still unsolved" list has not run this lens.

| Question | What a good answer looks like | Where the lesson came from |
|---|---|---|
| What decays, and what must never decay? | A `kind` on every row. Rules surface by trigger word and are never pruned by age; only facts age. | Link 3.0 measured recency decay and three other usage-aware rankings and declined them all: durable constraints do not become less true for going unread. |
| Are two contradictory facts resolved at write or at read? | At write, by a pure function of document order; the loser kept as an audit row. No model is asked "which is current?". | memore, post-graph-rag, TOKI. |
| Does every fact carry two clocks? | Valid time and belief time, and the date printed beside the fact wherever it is read. | Zep/Graphiti; post-graph-rag's largest single gain was validity dates in the prompt. |
| What does "verified" prove? | That the quoted text exists in the source at that version. Not that it is true. Say so on the page. | Cortex. |
| What is rejected before storage? | Pronoun subjects, predicates off the list, numbers without units; the refusal returned with its reason. | post-graph-rag's extraction-time gates. |
| Is the format enforced by code or by instruction? | Typed parameters in, a view renders out. No free-form writes. | The gist's thread: fixed-header tables, programmatic formatting. |
| Is stale / pending / gap a stored flag or a computed view? | Computed. A memory is questioned only when its pointer is missing now and existed before. | Link 3.0 `lnk stale`. |
| Does the system know whether it is consulted at all? | Consult rate logged per session; precision (used ÷ sent) reported beside recall. | The thread; Link 3.0: recall alone scores 1.0 by returning everything. |
| Who can write live, and who can only propose? | Verified writes from owned sources go live; rules, merges, guests and unverified extractions wait in proposals for one human tap. | The thread's write-gated proposals; TOKI's await-confirmation operator. |
| What happens when the store is unreachable? | Capture never blocks: a fallback inbox, timestamped by send time, reconciled later. | The thread: fail-open capture. |
| What is the benchmark, and can it rank anything? | An own probe set scored by exact match on an id, with a confidence interval; operations (update, forget, abstain) scored, not only answers. Never quote a public leaderboard about your own system. | The LoCoMo audit (6.4% of the key wrong; the judge accepts 62.8% of wrong answers); LongMemEval's five abilities; MemOps. |
| What happens when a step cannot produce a well-formed record? | It fails loudly and drops the record. Never a placeholder to keep the pipeline moving: a stand-in is indistinguishable from real structure once stored, and a transient outage poisons the store for good. | post-graph-rag. |
| Do the instructions describe shape or live values? | Shape only. No counts, ids or names in the boot line or the rules; live values come from a view, so nothing in the instructions can go stale. | MindBase's "state rule". |
| Is the system itself a lethal trifecta (private data + untrusted content + a way out)? | Name all three legs; put the defences at write time (admission, provenance, instruction shape, scope) and give any autonomous worker no way out. | Simon Willison (2025); OWASP ASI06 (2026); a hub build of 2026-09-26. |
| What leaves the private surfaces, and is that tested? | A test that greps every outbound message (push, digest, public repo) for the words that must never be there. Values *and* names: a subject or account name can leak what its values would. | The same build: the first digest carried no private values but named private subjects, a bank and a broker. |
| Is each lock proven by the next object, or by the statement that set it? | Create the next thing (a function, a table) and check its grants; run the audit that would catch the regression. | The same build: a schema-scoped default revoke left new functions public; the nightly audit caught it in a minute. |
| What is honestly unsolved? | Named on the page with its mitigation and the mitigation's limit. | memore: the same subject phrased two ways agreed 58% of the time. |

## The field scan — where to look, in order

1. The vendor's help center and platform docs (what the product does this month; features change monthly).
2. The comment thread under the primary source, read as an adversary of your draft. The counterarguments, the "measured and declined" notes and the implementers' scars live there, not in the post.
3. Anthropic news and platform changelog (memory tool, context management, connectors).
4. GitHub search and Product Hunt for the indie builders — the single-person versions are the closest to Dex's situation. Read the release notes, not the README; that is where a team says what it tried and dropped.
5. The audit of a benchmark before its leaderboard. If vendors dispute each other's numbers on it, the numbers rank nothing.
6. One or two roundups, only to find primary sources you missed.
7. The history: who named the idea first (academic paper, first open-source project), so the timeline is honest.

## Page section checklist

Six tiles · capability map · mechanism figure · mind map · math · lenses table · field table + new ideas · quality control (write-path figure, lesson table, the field's quality table, own probes, the unsolved list) · history · vocabulary · first three moves · sources.
