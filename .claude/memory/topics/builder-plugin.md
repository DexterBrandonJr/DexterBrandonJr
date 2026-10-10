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

## 2026-10-10 — Setup 5 of 6, the guard test, and one Builder

**Decisions:**
- **Dex accepted proposal 652.** The benchmark-and-report-in rule is live in the hub.
- **The setup checks itself off.** One-memory-hub migrations 0038 to 0040 add the `builder_setup` view: six steps, each marked done from evidence in the hub, never from a chat's say-so. The published setup page reads it through the artifact's Supabase connector and shows "You are here". Dex asked for this because he loses track of which step he is on.
- **One Builder, not two.** The plugin does not carry every innovation, engineering and growth prompt Dex wrote. Rather than a second plugin, Builder moves to a private repo once Cowork has collected his prompts (hub thread t:1197), and gains them, the full private doctrine and the red-team skill there. Dex switches marketplaces once.

**Facts / preferences:**
- **Proven: hooks did not run in two places.** In claude.ai web chat the model refused `export WEBULL_ENV=live` on its own, with no bl:443. In a desktop chat on the cloud workspace the command ran. Neither is a Cowork project task, so the guard inside Cowork is still Expected.
- **Step 1 had been inferred wrongly** from Cowork writing to the hub; 0039 made it require a recorded install instead.
- **A second 'status' fact superseded the first.** `status` is single-valued for a subject, so recording the schedule as a status replaced "installed". It was restored (supersede 77) and the schedule recorded under `uses`. Separate things on one subject go under `uses` or `fact`.
- **The Builder Boot schedule** runs weekdays at 7:10 in the Builder project with "Skip all approvals". Until the guard is proven in Cowork, asking before risky actions is the safer setting; that choice is Dex's.

**Artifacts:**
- one-memory-hub migrations 0038, 0039, 0040 (`builder_setup`)
- the setup page, with the "You are here" card and a hand-off-to-Builder button

**Open threads:**
- Step 4: the guard test inside a Builder project task in desktop Cowork (t:1107). A pass cites bl:443.
- t:1197: Cowork collects Dex's prompts into Drive; when he says "prompts are ready", build the private Builder.
