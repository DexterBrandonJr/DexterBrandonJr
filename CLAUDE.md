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

## Read the hub first

Dex keeps one memory for every Claude he talks to: a private Supabase
project named `one-memory-hub` (its repo is `DexterBrandonJr/one-memory-hub`,
private). At the start of a session that touches him, his projects or his
preferences, run `select * from hub_boot('code')` through the Supabase
connector on that project, follow the rules it returns, and write back last
with `hub_capture` / `hub_write` / `hub_used`. The chat-memory files in this
repo remain the per-repo record; the hub is the cross-surface one.

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
