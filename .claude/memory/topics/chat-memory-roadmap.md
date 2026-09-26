# chat-memory roadmap

## 2026-09-04 — Backlog from building v1

**Decisions:** Shipped v1 with: per-repo memory by default, global (`~/.claude/memory`) as an explicit opt-in via `CLAUDE_CHAT_MEMORY_DIR` or the auto-detecting `SessionStart` hook, curated distillation over raw transcript dumps, and a public-repo warning that's currently judgment-only (not enforced by code).
**Facts / preferences:** Dex wants chat-memory available on every repo he works in, including ones that don't exist yet — solved via installing the `.skill` package to his Claude.ai profile (syncs into every session) rather than per-repo setup.
**Artifacts:** `.claude/skills/chat-memory/` (skill), `.claude/skills/chat-memory/scripts/session_start_hook.sh` (auto-load hook, jq → python3 → pure-shell fallback), `.claude/skills/chat-memory/references/global-setup.md` (cross-project setup guide), PR #4 (skill + chat-memory, merged), PR #5 (SessionStart hook + global-setup, open).
**Open threads:** Prioritized follow-ups identified while building/testing v1, none yet implemented:
1. *Index growth control* — the SessionStart hook injects the full `INDEX.md` every session forever; once it accumulates many topics this becomes a permanent per-session context cost. Needs either a size cap on what the hook injects (most-recent N, with a note to search for the rest) or an archive/prune script for stale topics.
2. *Windows without Git Bash* — `session_start_hook.sh` is bash-only; Claude Code on native Windows without Git Bash runs hooks via PowerShell by default, so the hook silently never fires there. Needs a PowerShell twin or at least a documented limitation.
3. *Automated public-repo check* — SKILL.md currently asks Claude to manually judge whether a repo is public before saving; that's a judgment call that can be skipped under time pressure. Could add a small script that actually checks (e.g. via the git remote + a GitHub API lookup) instead of relying purely on prose instruction.
4. *Secret-scanning backstop* — `new_entry.py` writes whatever content it's given with no scan for obvious secrets (API keys, tokens, "password:", etc.). Worth a lightweight pre-write check as a backstop beyond "use good judgment," given how easily an unrelated fact can carry a pasted secret along with it.
5. *Topic dedupe tooling* — "keep the index honest" (merge near-duplicate topics) is currently manual-only guidance in the SKILL.md with no tooling support. A `--list`/`list_topics.py` that shows existing topics with summaries before creating a new one would reduce near-duplicate topics accumulating over time.
6. *Entry staleness* — some saved facts have a shelf life (e.g. "as of Q3, using X"); nothing currently distinguishes a permanent fact from a time-bound one, so an old entry can get treated as still-true indefinitely. Consider an optional `as-of:`/`stale-after:` field.
7. *Formal eval suite* — the only trigger-testing done so far was 4 ad hoc subagent runs in-session. Worth formalizing into a saved `evals/` set (per skill-builder's own methodology) so future SKILL.md edits can be regression-tested rather than manually re-verified each time.
8. *Pre-push preview for high-stakes saves* — the skill states back what was saved after it's already committed and pushed. An optional explicit preview step (e.g. surfacing `git diff --cached`) before pushing to a public repo specifically would catch a bad entry before it's irreversible/public, not just after.
9. *Multi-machine global sync* — `references/global-setup.md` documents pointing `CLAUDE_CHAT_MEMORY_DIR` at a private git repo for memory shared across machines, but there's no helper script for it yet — it's fully manual git add/commit/push today.

## 2026-09-04 — Round 2: shipped 4 of 9

**Decisions:** Shipped items 1 (index growth control), 4 (secret-scanning backstop), 5 (topic dedupe/listing), and 8 (pre-push preview ordering) from the original nine. Deferred 3 (public-repo check), 6 (entry staleness), 7 (formal eval suite), 2 (Windows/PowerShell twin), and 9 (multi-machine sync) — each has a written execution protocol in `references/roadmap.md` for whenever they're picked up, rather than being guessed at and shipped half-verified.
**Facts / preferences:** Dex wants both detailed execution plans (not just a task list) and a visual system map when asking for follow-up work like this — delivered as `references/roadmap.md` (protocol per item) plus the "Efficiency Web" artifact (diagram of how the pieces feed back into each other).
**Artifacts:** `scripts/scan_for_secrets.py`, `scripts/list_topics.py` (new), `scripts/session_start_hook.sh` (index cap added), `SKILL.md` Saving section (reordered), `references/roadmap.md` (new — protocol for all 9 items). Also fixed a real bug found via testing: `skill-builder/scripts/validate_skill.py` was flagging valid repo-root-relative script references as missing. Efficiency Web diagram: https://claude.ai/code/artifact/c85cb13b-e96c-4ef2-bf8a-76f0c19d8a9d
**Open threads:** The 5 deferred items above remain open, each with a protocol written but not executed — see `references/roadmap.md` for what "done" looks like on each before picking one up.

## 2026-09-26 — new_entry.py leaves the index out of recency order

**Decisions:** Found a real bug in the tooling rather than in an entry. `new_entry.py` updates a topic's `updated` date in `INDEX.md` **in place**, without moving its line, so adding an entry to an older topic leaves it sitting below newer ones. Caught it when the check-in-cadence topic, dated that day, appeared below entries from the sixth. Re-sorted by hand (stable sort on the date, descending, trailing comment block preserved) and committed the fix to the file, but **the script itself is unchanged and will do it again**.

**Facts / preferences:** Recency order is the one property the index exists for — the `SessionStart` hook injects it whole every session, and its value is that the freshest topics are the ones read first. A silent re-order defeats that without anything looking wrong, which puts it in the same family as the other checks-that-establish-nothing collected in `working-with-claude.md`.

**Artifacts:** Hand fix in commit `e72b56f`. The bug is in `scripts/new_entry.py`, in whichever step rewrites the pointer line.

**Open threads:** New roadmap item, on top of the five still deferred from round 2: **make `new_entry.py` re-sort the whole index after updating a pointer line**, rather than editing it where it sits. Small and self-contained — the sort is by the date in each line, descending, stable within a date, leaving the trailing HTML comment alone. Worth doing before the next time someone trusts the order.
