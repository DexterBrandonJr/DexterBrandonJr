# Builder Plugin

## 2026-10-08 — Builder Plugin

Dex asked for a Cowork project that builds the way the Code chat does, works with it, and is robust and intuitive.

**Decisions:**
- **One plugin, installed on the account.** Cowork loads skills, hooks and commands from the claude.ai account, never from a repo's `.claude/`. So the Cowork side ships as `plugins/builder`, listed by `.claude-plugin/marketplace.json` in this public repo.
  - Every packaged file was already public here.
  - A public marketplace avoids a reported bug where Cowork could not add a private GitHub marketplace.
- **Six skills are packaged:** hub, workhorse, phased-build, innovation-brief, scenarios and tandem. Three are left out:
  - qc-lead, because there is one lead and it is the Code chat;
  - chat-memory and skill-builder, because they are already on the account;
  - autopatch, because it is repo-bound.
- **The skills are copies made by `plugins/build.py`.**
  - It rewrites `.claude/skills/<name>/<file>` to `${CLAUDE_SKILL_DIR}/<file>`, only for files the skill ships, because workhorse's pointer into the private repo must stay as written.
  - It raises the version whenever the content digest changes. A set `version` pins every install, so a change without a bump would never reach Cowork.
  - It writes a byte-stable, uncompressed `plugins/builder.zip` for the upload fallback. Deflate output varies by zlib version, which would break the byte check.
- **Handoffs between Cowork and Code are hub threads** (`hub_handoff`, owner `claude:cowork` or `claude:code`). Dex carries at most one line: `/builder:pickup t:<id>`.

**Facts / preferences:**
- **Proven:** `claude plugin validate` passes for the plugin and the marketplace. The CLI installed `builder@dexterbrandonjr` from the local marketplace. The installed copy of the guard refused `export WEBULL_ENV=live` sent as `mcp__workspace__bash`.
- **Tested:** `plugins/tests/test_builder.py` has 15 tests and is stdlib only. It covers:
  - the guard under Bash, PowerShell and `mcp__workspace__bash`;
  - matcher coverage;
  - drift and the version bump;
  - manifest and marketplace agreement;
  - frontmatter;
  - no `bin/`;
  - a personal-data scan.

  A broken matcher and a planted SSN were each seen to fail it.
- **A plugin installed on the account syncs into Claude Code** at the next session start (Anthropic's plugin platform-support page). Hooks run in Cowork and Code; chat ignores agents and hooks.
- **Docs disagree on where Cowork projects live.** The developer docs say on the Mac only; the help center says "from scratch" projects are saved to the account.
- **`hub_handoff` matches open threads by title.** With an open thread's title, it only rewrites that thread's next step and keeps its owner. Moving t:101 to Cowork that way closed the work itself. It was repaired as t:1106, and the tandem skill now says to close first and then hand off.

**Artifacts:**
- `plugins/builder/` (skills, commands, the `qc-reviewer` agent, hooks)
- `plugins/build.py`, `plugins/tests/test_builder.py`, `plugins/builder.zip`
- `.claude/skills/tandem/SKILL.md` (the canonical copy)
- `docs/COWORK.md` (the setup); a published setup page

**Open threads:**
- Dex's first run in Cowork (docs/COWORK.md, section 4) is the only proof the guard runs inside Cowork's sandbox. Until then that is Expected.
- t:1106 (ER equipment map) and t:1104 (Quint 24 workbook) wait for Builder.

## 2026-10-10 — Benchmark and report in; the first Cowork setup

**Decisions:**
- **Dex's rule (raw 1438, 1439):** every build ends with a benchmark row and a one-line progress note through the hub. The hub, the repos, the Code builder chat and the Builder project move in lockstep. The rule is in the hub as proposal 652, which waits on Dex's "accept 652": the hub keeps every rule for a human.
- **The mechanism is one table, not two habits.** One-memory-hub migration 0037 adds `benchmarks`, `hub_benchmark(...)` (refuses a row with no measurement method or note; `improved` is computed) and `builder_progress`, which `/builder:boot` reads.
- **The rule block went into the CLAUDE.md of all 11 repos** and the doctrine (§2 item 11), each by pull request. health-tracker had no CLAUDE.md, so it got a short one.
- **The approval line now reads:** "Do the whole batch and don't re-ask for approval he already gave. Ask first before anything that sends, pays, posts or can't be undone."

**Facts / preferences:**
- **The Builder chat in Cowork could not write its own project Instructions, a standing rule or a cross-repo handoff.** A safety check requires Dex to supply text that future Claudes will follow. That is by design; the setup doc says so.
- **On first setup the Instructions were pasted into the Description box.** The Builder chat caught it and Dex fixed it.

**Open threads:**
- The guard test inside Cowork (t:1107) is still unproven.
- Proposal 652 waits on Dex.
