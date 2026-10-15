- [Builder Plugin](topics/builder-plugin.md) — updated 2026-10-10 — Builder setup 5 of 6 done (builder_setup view reads it); the guard is unproven in Cowork because web chat and the cloud-workspace chat run no hooks; one Builder, moving to a private repo once Dex's prompts are collected (t:1197)
- [Model Coaching System](topics/model-coaching-system.md) — updated 2026-10-02 — Four Claude Code newsletters and their links read into the hub (raw 1104, 52 facts, 12 subjects); Sonnet 5.5 added to the catalog (0027); test phase on Sonnet 5.5, debug starts Fable 5.1 at medium
- [One Memory Hub](topics/one-memory-hub.md) — updated 2026-09-30 — bl:365 built: a chat can read what a hub write takes before it writes, and every refusal names the fix
- [Wealth Engine](topics/wealth-engine.md) — updated 2026-09-28 — Dex's household finance system (accounting, taxes, insurance, budgeting, debt, credit, investing, wealth management, coaching) lives in the private repo DexterBrandonJr/wealth-engine; this repo keeps the pointer only
- [Artifact Listen](topics/artifact-listen.md) — updated 2026-09-28 — narrate_system.py + system-shell.html: one player that keeps playing across views and tiers, re-records only changed views; medium voice now default (5.4x faster, same clarity); failure bets 170-174 in the hub
- [Chat Memory Roadmap](topics/chat-memory-roadmap.md) — updated 2026-09-26 — new_entry.py now re-sorts the whole index by date, newest first; the recency-order bug is fixed in the script, not by hand
- [Qc Lead](topics/qc-lead.md) — updated 2026-09-26 — the QC lead chat reads every change, gives each one verdict, and closes a pass only when nothing is unread; one writer per repo everywhere
- [Github Integration](topics/github-integration.md) — updated 2026-09-26 — The draft-to-ready flip worked; send it alone
- [Working With Claude](topics/working-with-claude.md) — updated 2026-09-26 — when Dex says he is asleep, on shift or away, routine approvals for that window are already given; the tools go on the project allowlist, what truly needs his hand goes on the morning list
- [Claude Starter File](topics/claude-starter-file.md) — updated 2026-09-26 — share/hub-kit v1.1: hub.route in SQL and Python (24/24 each), hub_import.py for notes folders and ChatGPT/Claude exports, hub.config.example.json; artifact republished
- [Scenarios](topics/scenarios.md) — updated 2026-09-26 — skill scenarios: Monte Carlo that halts when settled (1 to 10,000 runs), arms on shared draws, every factor labeled measured/estimated/emerging/speculative from a 129-node catalog; Python and the hub's SQL engine agree draw for draw
- [Upscayl Wrap](topics/upscayl-wrap.md) — updated 2026-09-16 — Upscayl CLI wrapper built; engine exit code carries no information
- [Pr Checkin Cadence](topics/pr-checkin-cadence.md) — updated 2026-09-16 — weekly on Thursdays, the low-activity day; violated again by an hourly per-PR check-in — reaching for send_later on a PR is the moment to re-read this
- [Workhorse](topics/workhorse.md) — updated 2026-09-15 — the scaffold script run for the first time (proven, 10 files, one trading leak found); the domains playbook now derives a row for any topic instead of listing seven
- [Trading Engine](topics/trading-engine.md) — updated 2026-09-10 — moved to the private repo; a history rewrite would NOT remove it (GitHub PR refs), checked and recorded
- [Macos Contextual Search](topics/macos-contextual-search.md) — updated 2026-09-07 — PR #1 merged
- [Acronym Spellout Preference](topics/acronym-spellout-preference.md) — updated 2026-09-06 — Spell out and explain all acronyms in responses
- [Tool Blueprint Workflow](topics/tool-blueprint-workflow.md) — updated 2026-09-06 — Fill the tool_blueprint template once a plan is agreed
- [Chat Scope Apps And Tools](topics/chat-scope-apps-and-tools.md) — updated 2026-09-06 — Chat scope expanded: skills + apps/functions/tools
- [cross-session trigger hygiene](topics/cross-session-trigger-hygiene.md) — updated 2026-09-05 — verifiable cross-session asks need surviving evidence, not just trust
<!--
Chat-memory index. One line per topic, most-recently-updated first:

- [<title>](topics/<slug>.md) — updated <YYYY-MM-DD> — <one-line summary>

Managed by .claude/skills/chat-memory/scripts/new_entry.py — see that
skill's SKILL.md before hand-editing this file. This repo is public,
so treat every entry as public: no secrets, credentials, or anything
you wouldn't want visible on a public GitHub profile.
-->
