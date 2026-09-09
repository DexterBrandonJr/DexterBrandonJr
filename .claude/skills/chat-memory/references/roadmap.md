# Roadmap: Execution Plans and Protocols

Detailed plan for each item on the chat-memory backlog (see the `chat-memory roadmap` memory entry for the original list). Each item states the goal, the approach, the build/test protocol used to verify it, and its status. Shipped items link to the commit that shipped them; planned items are written up in enough detail to pick up and build later without re-deriving the design.

## Table of contents

1. Secret-scanning backstop — SHIPPED
2. Index growth control — SHIPPED
3. Topic dedupe / listing tool — SHIPPED
4. Pre-push preview ordering — SHIPPED
5. Automated public-repo check — PLANNED
6. Entry staleness marking — PLANNED
7. Formal eval suite — PLANNED
8. Windows / PowerShell hook twin — PLANNED
9. Multi-machine memory sync helper — PLANNED

---

## 1. Secret-scanning backstop — SHIPPED

**Goal:** catch an obvious secret (API key, token, private key block, password) riding along inside an otherwise-innocuous memory entry, before it's committed — the SKILL.md warning about public repos is prose-only and can be skipped under time pressure; this is a mechanical backstop, not a replacement for judgment.

**Approach:** a standalone scanner (`scripts/scan_for_secrets.py <file>`) run against a filled-in topic file right before commit. Pattern-based, not full entropy analysis — deliberately biased toward catching well-known credential *shapes* (AWS keys, GitHub tokens, Slack tokens, PEM private-key blocks, `key: value`-style assignments to secret-sounding field names) rather than flagging every long string, to keep false positives low enough that the check doesn't get reflexively ignored.

**Protocol:**
- Unit-tested against one clean sample (must pass) and one sample per pattern class (AWS key, GitHub token, Slack token, PEM block, `password:`/`secret:`/`token:`-style assignment) — each must be caught.
- Explicit false-positive check: plain prose that *discusses* passwords/secrets/tokens without an actual value attached must not trigger.
- Wired into `SKILL.md`'s Saving workflow as a required step between filling in content and committing.

**Status:** shipped. Script: `scripts/scan_for_secrets.py`. Test transcript in the commit that added it.

## 2. Index growth control — SHIPPED

**Goal:** the `SessionStart` hook injects the *entire* `INDEX.md` every session, forever. Fine at 3 topics; not fine at 300 — that's a permanent per-session context tax that grows without bound and never gets smaller on its own.

**Approach:** cap what the hook actually injects to the N most-recently-updated index lines (index is already maintained most-recent-first by `new_entry.py`), and append a one-line note when truncated ("+K more topics — run `search_memory.py <query>` to find them"). Cap is configurable via `$CLAUDE_CHAT_MEMORY_INDEX_CAP` (default 20) so it's not a hardcoded guess.

**Protocol:**
- Synthetic `INDEX.md` with 50 topic lines → hook output contains exactly the cap's worth of lines plus the truncation note with the correct remaining count.
- Small `INDEX.md` (below cap) → output unchanged, no truncation note.
- Re-verified the jq / python3 / pure-shell fallback paths still produce valid JSON with the truncated content (the truncation happens before the encoding step, so all three encoders see the same bounded input — but re-tested rather than assumed).

**Status:** shipped. `scripts/session_start_hook.sh` updated in place.

## 3. Topic dedupe / listing tool — SHIPPED

**Goal:** "merge near-duplicate topics" (SKILL.md's "Keep the index honest" section) was manual-only guidance with no tooling — nothing surfaced existing topics before a new one got created, so duplication was easy to fall into by accident.

**Approach:** `scripts/list_topics.py <memory-dir>`, a read-only companion to `new_entry.py`'s write path. Parses `INDEX.md`, prints each topic's title, slug, last-updated date, and summary. `SKILL.md`'s "decide the topic" step now points here first when it's not obvious whether a similar topic already exists.

**Protocol:**
- Memory dir with several real topics → each listed correctly, sorted as `INDEX.md` already sorts them.
- Memory dir with only the empty template `INDEX.md` (no real topics yet) → clean "no topics yet" message, not a crash on the HTML comment block.

**Status:** shipped. Script: `scripts/list_topics.py`.

## 4. Pre-push preview ordering — SHIPPED

**Goal:** the skill used to state back what it saved *after* committing and pushing — on a public repo, that means the human's first look at the exact content is after it's already gone out, not before.

**Approach:** no new code — a documentation-only reorder. `SKILL.md`'s Saving steps now put "state back exactly what you're about to save" *before* `git push` (still after the local, reversible `git commit`), so the narration of what's going out is part of the same turn as the push rather than a report filed afterward. This isn't a hard blocking confirmation gate — deliberately: an earlier design pass already weighed a synchronous "wait for approval on every save" gate against a lightweight "state it plainly" fix and picked the lightweight one, reasoning that memory-saves are meant to be low-friction and a hard gate on every single save would undermine the feature. This step keeps that same posture, just fixes the ordering so the statement lands before the shared/public action instead of after it.

**Status:** shipped. `SKILL.md` Saving section reordered.

---

## 5. Automated public-repo check — PLANNED

**Goal:** replace "check whether the repo is public" (currently a prose instruction Claude has to remember and judge every time) with something that actually checks.

**Approach:** a script (e.g. `scripts/check_repo_visibility.py`) that runs `git remote get-url origin`, parses the owner/repo, and either (a) calls the GitHub REST API's unauthenticated repo endpoint (public repos return 200 with `"private": false`; this works without a token for public repos, and a 404 on a private repo without auth is itself informative-but-ambiguous — can't fully distinguish "private" from "doesn't exist" without a token) or (b) if a `gh`/GitHub MCP tool is available in-session, use that instead for an authoritative answer including private repos. Exit code or printed verdict Claude reads before deciding whether to warn.

**Why not shipped this round:** needs a live network call (or an available GitHub tool) to verify against a real repo, and the unauthenticated-API ambiguity above needs a real design decision (fail open with a warning, or fail closed and always ask) rather than a guess — worth a short back-and-forth rather than shipping a guessed default.

**Protocol when built:** test against a known-public repo (should report public), and against a private repo the session has access to via the GitHub MCP tools (should report private) — using the GitHub tools already available in-session as the authoritative path, with the unauthenticated-API path as a fallback when no such tool exists, clearly labeled as "best-effort" in its output.

## 6. Entry staleness marking — PLANNED

**Goal:** some saved facts have a shelf life ("as of Q3 2026, using Vite") and nothing today distinguishes that from a permanent fact ("Dex's contact email is..."), so an old, time-bound entry can silently get treated as still-true indefinitely.

**Approach:** an optional `as-of:` field alongside the existing four (Decisions / Facts / Artifacts / Open threads) in the entry schema (`references/schema.md`), populated only when the content itself is inherently time-bound. On recall, a stale-looking `as-of:` (e.g. more than N months old, or simply present at all) gets flagged in Claude's own response rather than silently treated as current ("this was true as of Mar 2026 — worth confirming it still is").

**Why not shipped this round:** this is a schema change, not just a script — it needs `new_entry.py`'s template updated, `references/schema.md` updated, and a judgment call folded into the Recalling section of `SKILL.md` about *when* something counts as time-bound in the first place (that line is genuinely fuzzy and deserves a beat of design thought rather than a rushed default).

**Protocol when built:** write one entry with `as-of:` and one without; recall both and confirm only the dated one gets an explicit "worth confirming" flag in the response.

## 7. Formal eval suite — PLANNED

**Goal:** the only trigger-testing chat-memory has had is 4 ad hoc subagent runs done manually in a single skill-builder session. That's real signal, but it's not repeatable — there's no saved eval set to re-run the next time `SKILL.md`'s description or workflow changes, so regressions would only be caught by another round of manual testing (or not at all).

**Approach:** formalize into `evals/evals.json` per `skill-creator`'s own schema (should-trigger and shouldn't-trigger prompts, the same four used in the original manual test plus a wider should/shouldn't set per `skill-builder`'s Step 7 guidance — 8-10 of each rather than 2 of each). Store it inside the skill package so it travels with it.

**Why not shipped this round:** the full version of this (parallel subagent runs, blind grading, benchmark aggregation) is `skill-creator`'s heavyweight machinery, not something to improvise partially — worth running properly in one dedicated pass rather than a partial version now.

**Protocol when built:** follow `skill-creator`'s own eval-set-creation and `run_loop` process directly rather than reinventing it; save results under `chat-memory-workspace/` alongside the skill per that skill's own convention.

## 8. Windows / PowerShell hook twin — PLANNED

**Goal:** `session_start_hook.sh` is bash-only. Claude Code on native Windows without Git Bash runs hooks via PowerShell by default (per the hooks schema's `shell` option) — on that setup, the hook silently never fires. No error, no warning: memory just never auto-loads, and nothing about that failure is visible.

**Approach:** a `session_start_hook.ps1` twin implementing the same resolution order (`$env:CLAUDE_CHAT_MEMORY_DIR` → project `.claude\memory` → `~\.claude\memory` → no-op) and the same `hookSpecificOutput.additionalContext` JSON shape, referenced via a second hook entry with `"shell": "powershell"` (or documented as a manual alternate setup step in `references/global-setup.md`).

**Why not shipped this round:** no verified Windows/PowerShell environment available in this session to actually test it against — writing an untested PowerShell script and calling it done would violate the same "test, don't assume" standard the bash version was held to.

**Protocol when built:** must be verified on an actual PowerShell host (pipe a synthetic stdin payload through it, as was done for the bash version) before being called shipped, not just written by analogy to the bash script.

## 9. Multi-machine memory sync helper — PLANNED

**Goal:** `references/global-setup.md` documents pointing `$CLAUDE_CHAT_MEMORY_DIR` at a private git repo so personal memory can follow you across more than one machine, but today that means manually `cd`-ing there and running `git pull`/`git push` yourself around every save — easy to forget, and a forgotten pull means a stale local copy silently diverging from what's on the remote.

**Approach:** a thin wrapper script that `new_entry.py` and `search_memory.py` can optionally call through — `git pull --rebase` (or equivalent) before reading, `git add . && git commit && git push` after writing, when `$CLAUDE_CHAT_MEMORY_DIR` is itself a git repo. Should degrade to today's fully-manual behavior when the memory dir isn't a git repo at all (e.g. this repo's own `.claude/memory`, which is part of a larger repo Claude already manages directly).

**Why not shipped this round:** lower priority than the four shipped this round — no evidence yet that multiple machines are actually in play for this user, and building sync machinery ahead of an actual need risks exactly the kind of speculative feature `skill-builder`'s own "don't design for hypothetical future requirements" principle warns against. Worth building once there's a real second machine to test it against.

**Protocol when built:** test with two separate local clones of the same throwaway memory repo, simulating two machines — save from clone A, confirm a subsequent read from clone B sees it after the wrapper's pull step, with no manual git commands run by hand.
