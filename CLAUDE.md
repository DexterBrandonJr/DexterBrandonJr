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
- `.claude/memory/` — the actual memory store (`INDEX.md` + `topics/`).
  **This repo is public** — nothing sensitive goes in here. See the skill's
  public/private/never-in-git guidance before writing an entry; some things
  (identity-critical secrets) don't belong in *any* git repo, public or
  private.

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
