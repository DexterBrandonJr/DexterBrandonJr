# DexterBrandonJr/DexterBrandonJr

This repo is Dexter's public GitHub profile repo (its `README.md` renders on
his GitHub profile page) *and*, separately, the home base for how he builds
things with Claude Code.

## What lives here

- `.claude/skills/skill-builder/` — a meta-skill for designing, drafting,
  validating, and tuning new Claude Skills (SKILL.md packages).
- `.claude/skills/chat-memory/` — git-backed memory that persists facts,
  decisions, and open threads across separate chats and sessions instead of
  losing them when a session ends. Auto-loads via a `SessionStart` hook.
  Read its `SKILL.md` before hand-editing anything under `.claude/memory/`.
- `.claude/skills/phased-build/` — how the work is *run*: build → test → debug
  → fix as separate phases Dex starts himself, his standing execution contract
  ("do it all, approve everything, don't stop"), the quality-control gate
  before he sees anything, and `scripts/ci_cost.py`, which prices one merge in
  continuous-integration minutes before the work starts rather than after.
- `.claude/skills/workhorse/` — the domain-neutral core of how Dex prefers
  systems built (the eight parts, the rhythm, the confidence contract), and
  how to reach the full doctrine in the private `DexterBrandonJr/workhorse`
  repo. Triggers on any new build in any domain.
- `.claude/skills/scenarios/` — settles a what-if with a Monte Carlo
  simulation that stops as soon as the answer is settled (1 to 10,000 runs),
  compares configurations on the same random draws, and labels every factor
  measured, estimated, emerging or speculative from a 129-node catalog
  (`references/domains.json`). `scripts/scenarios.py` runs anywhere; the
  private hub runs the same engine in the database and matches it draw for
  draw.
- `.claude/skills/qc-lead/` — how one chat leads quality control over many
  parallel chats: it reads every change since its last pass, re-runs the
  proof of what it built, gives every change one verdict (kept, folded,
  fixed, reverted, flagged, noted, or one copy-paste prompt for Dex), and
  closes a pass only when nothing is unread. `references/chat-report-prompt.md`
  is what Dex pastes into every chat when the lead needs their state. The
  private hub keeps the ledger.
- `tools/upscayl-wrap/` — a command-line wrapper for the Upscayl photo
  upscaling engine, built around what the engine gets wrong. Generic and
  public-safe; its README and memory topic carry the details.
- `.claude/memory/` — the actual memory store (`INDEX.md` + `topics/`).
  **This repo is public** — nothing sensitive goes in here. See the skill's
  public/private/never-in-git guidance before writing an entry; some things
  (identity-critical secrets) don't belong in *any* git repo, public or
  private.

- `share/claude-starter/START-HERE.md` — a single file to hand to someone
  who is new to Claude (Windows, Pro plan, chat only, easily overwhelmed).
  Their Claude reads it, gets them to a made thing on day one, walks setup
  at their pace, offers two doors to file work (desktop app, or the
  terminal taught one command at a time), climbs a ladder of one-file
  tools they can double-click, keeps their usage low, and carries a
  plain-language cut of the workhorse build questions. Deliberately **not** named `CLAUDE.md`: a `CLAUDE.md` in
  a subdirectory here would load as directory-scoped instructions into
  Dex's own sessions. Generic and public-safe by design.

- `share/hub-kit/` — the **Hub Kit**: `HUB-KIT.md` is one file anyone can
  give to any AI ("Run the Hub Kit.") to install their own version of the
  hub: paper, local (Python + SQLite) or cloud (a Postgres schema `hub`),
  with consent cards before every signup, human-step blocks, teaching,
  predictive answers, a self-test and a security audit. Generic and
  public-safe; rebuild with `python3 share/hub-kit/src/build.py` after
  editing `src/protocol.md`, `hub-kit.sql` or `hub_local.py`.

- `docs/MODELS.md`, `models.json`, `supabase/migrations/` — the **model
  coaching system**: which Claude model and effort to start with in each
  build phase (house defaults, marked as such), the checked model facts,
  and the coaching slice of the hub's schema — every run logged, advice
  computed nightly from the runs, a pick on request. Chats log runs and
  ask for picks through the `hub` skill ("what model should I use").
  The hub's own migrations live in its private repo; only the coaching
  ones are here.

- `plugins/builder/` + `.claude-plugin/marketplace.json` — the **Builder
  plugin**, how Cowork builds the way this repo does. Cowork reads plugins
  from the claude.ai account, never a repo's `.claude/`, so this packages
  six skills for it: `hub`, `workhorse`, `phased-build`, `innovation-brief`,
  `scenarios` and the new `tandem` (which surface does what, and handoffs
  as hub threads). It also carries the never-lines hook, `/builder:boot`,
  `handoff`, `pickup` and `qc`, and a `qc-reviewer` agent. An account
  install also syncs into Claude Code. The skills are copies: edit the
  originals in `.claude/`, then `python3 plugins/build.py` (it raises the
  version and rewrites `plugins/builder.zip`). `python3
  plugins/tests/test_builder.py` fails on drift. Setup: `docs/COWORK.md`.

- `share/artifact-listen/` — the **Listen control every artifact page
  carries** (`listen.html`): it reads the page aloud with pause, stop, a
  section picker and a speed; figures by their captions, tables row by
  row; nothing plays until a tap. The browser's own speech stops when a
  phone leaves the page, so `narrate.py` records the same text once with
  an offline voice into an MP3 the bar plays instead, which keeps going
  with the screen off or in another app, starts itself when the page
  opens (first tap anywhere where the phone refuses) and resumes where
  the listener stopped. For a system of many pages or tiers,
  `narrate_system.py` records each view (only the changed ones) and writes
  a player that keeps playing as the views change. Paste the block before the
  closing tag of the page's wrapper; publish the MP3 beside the page. The
  innovation-brief template already has the bar built in.

- `DexterBrandonJr/wealth-engine` (private, not here) — the **OSCAR Wealth
  Engine**: Dex's household financial analyst system, built the workhorse
  way. Its docs, schema and simulator live there; money detail lives in its
  vault, never in any repo; this repo keeps a pointer in
  `.claude/memory/topics/wealth-engine.md` and nothing sensitive.

## Read the hub first

Dex keeps one memory for every Claude he talks to: a private Supabase
project named `one-memory-hub` (its repo is `DexterBrandonJr/one-memory-hub`,
private). At the start of a session that touches him, his projects or his
preferences, run `select * from hub_boot('code')` through the Supabase
connector on that project, follow the rules it returns, and write back last
with `hub_capture` / `hub_write` / `hub_used`. The chat-memory files in this
repo remain the per-repo record; the hub is the cross-surface one.

## Parallel chats and the QC lead

Several chats work on Dex's repos at once. One writer per repo: every
session works in its own clone or worktree, lands changes through a pull
request, and stops there. The QC lead, the chat named in the hub, merges
other chats' pull requests, deletes branches and reconciles every change
against the design (skill `qc-lead`). When a chat needs Dex to do
something, it gives him one copy-paste prompt or command.

## Scope: skills, apps, functions, and tools — not just skills

This chat isn't limited to building Claude Skills. Dexter also uses it to
plan and build standalone apps, functions, and tools for his own goals
(e.g. local automation on his Mac, other one-off utilities). Those get
their **own dedicated repo** — usually private, since they tend to involve
personal data, a specific machine, or things that don't belong on a public
profile — rather than living inside this one. This repo stays the
coordination point: a chat-memory entry here records what a given project
is, why it exists, and where its actual repo lives, even though the
project's code doesn't.

## Known constraints worth remembering every session

- **The never-lines are held in code.** `.claude/hooks/never_lines.py` (a
  PreToolUse hook) and the deny rules in `.claude/settings.json` refuse every
  broker order tool, any live-trading switch and the live account map, in
  every permission mode. The same hook guards trading-engine and
  wealth-engine (hub bl:443). A rule stated only in chat can be lost to
  compaction; one that must hold belongs here.
- **This session runs in an isolated cloud container, not on Dexter's local
  machine.** Anything needing local filesystem access, OS/admin
  permissions, or a GUI app running on his Mac has to be handed to *him*
  (or to a separate, local Claude Code session running on that machine) to
  actually execute — this session can write the code but cannot run,
  install, or grant permissions for it on his hardware.
- The GitHub App installed for this account previously lacked the
  Administration permission needed to create new repositories via the API
  (a confirmed 403 — not fixable by reconnecting OAuth). As of 2026-09-06
  that's no longer blocking — `create_repository` succeeded (created
  `DexterBrandonJr/macos-contextual-search`, private). If it 403s again in
  the future, treat that as a regression and fall back to Dexter creating
  the empty repo himself.

## Benchmark and report in (Dex's rule, 2026-10-10)

Every build ends with one row in the hub, written in the same session:

```sql
select * from hub_benchmark('<build>', '<metric>', <before>, <after>,
  '<how it was measured: a test, a query, a timed run>',
  '<one-line progress note for the Builder project>',
  '<unit>', 'higher' /* or 'lower': which way is better */,
  '<repo>', '<surface>', 'claude:<surface>');
```

- The row is the benchmark. Whether it `improved` is computed from before
  and after, never claimed, and a row with no measurement method is refused.
- Its note is the progress report. The Builder project in Cowork reads
  `builder_progress` at every boot, so every chat's progress reaches it.
- Lockstep: the hub, the repos, the Claude Code builder chat and the Builder
  project move together. A rule changed in one of them is changed in all of
  them in the same session.
