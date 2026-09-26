# Claude Starter File

## 2026-09-16 — A file to hand to someone new to Claude

**Decisions:** One Markdown file, `share/claude-starter/START-HERE.md`,
written to Claude with five lines at the top for the human: save it, attach
it, say "read this and help me get started." The same file works attached to
a chat, pasted into a Project's instructions, or saved as `CLAUDE.md` in a
folder for the desktop app or Claude Code, where it loads itself. Named
`START-HERE.md`, not `CLAUDE.md`, on purpose: a `CLAUDE.md` in a
subdirectory here would load as directory-scoped instructions into Dex's own
sessions.

The centre of the design, after three rounds with Dex:

- **The thing they make is one file they can double-click.** A web page — a
  deadline countdown, a flashcard quiz from their own notes. Claude writes
  it; they open it. No install, no terminal to use it, costs nothing to run
  ever, visibly theirs. Four rungs: the deadline list from a syllabus (chat,
  day one), a folder that remembers (`TODO.md` as the record), the first
  built thing, then only what annoyed them that week. *Chat asks; the folder
  makes. Show, then name.*
- **Two doors to file work, chosen once:** the desktop app (no typing,
  recommended first) or the terminal track — PowerShell, about a dozen
  commands one per message across three sittings, then Claude Code lives in
  it. Neither hidden, neither forced.
- **The same shape every time.** Every setup message is "Step N of M ·
  about X minutes / one instruction / done or skip." Every session opens
  with "where we left off / one thing for today / go, change it, or skip."
  Times in minutes, never "quick." Transitions announced. One option, then
  "or no." A wrong command is "nothing happened." Short replies (*idk, ugh,
  k*) read as overload. "Keep going, or stop here?" instead of cutting off.
- **First reply is value, not setup.** Setup is offered after a first win,
  one phase per sitting, each opt-in; stuck twice on a step means stop.
- **Usage discipline is Claude's job:** Sonnet by default, short replies, a
  fresh chat when one gets long, files into the Project once. Made tools
  run free forever, which is the trade the ladder rests on.
- **Memory with no setup:** a five-line "remember this" block at the end of
  a chat, pasted under one heading in the Project instructions; the session
  opener reads from it.
- The workhorse derivation cut to four plain questions — what happens over
  and over, what can't be undone, what has to happen even when you forget,
  how will you know it's working — then the smallest version for a week.

**Facts / preferences:** Written for someone on Windows, on the Pro plan,
chat-only, using Claude for school and everyday questions, who gets
overwhelmed easily. No diagnosis named in the file (see
`working-with-claude`, 2026-09-16). Product details that drift — button
names, install commands — are written as "look for" with "tell me what you
see on the screen" as the fallback, and Claude is told to read the official
docs page before handing over any install command. 431 lines; read once
per Project, not per message.

**Artifacts:** `share/claude-starter/START-HERE.md` on `main` (pull
requests 26, 28, 30 — the last is the current shape); a bullet in
`CLAUDE.md` under "What lives here." Shareable as the raw GitHub link.

**Open threads:** Nobody has used it yet. The first real session with the
friend is what tests it; whatever confuses them is the next edit. Unverified
from here: whether the desktop app's folder mode is available on their
Windows build, and the current Windows install command for Claude Code —
the file tells Claude to check both rather than assert them.

## 2026-09-26 — Hub Kit: a hub anyone can install with any AI

**Decisions:**
- A second shareable file next to the starter: `share/hub-kit/HUB-KIT.md`. Anyone attaches it to any AI and says "Run the Hub Kit"; the AI installs their own version of the hub, the same call and response as Dex's (boot → brief → work → used), at one of three levels: paper (a `HUB.md` any AI reads), local (one stdlib Python file + SQLite, owner-only permissions), or cloud (a Postgres schema `hub`, Supabase free tier, reached through the Supabase MCP connector by any AI that speaks MCP).
- Three promises outrank everything in the file: nothing without a yes (a "before you sign up" card for every account, connector and install: what it can see, cost, undo, safer setting), no secrets in the chat, and the truth about what happened (Proven / Tested / Expected; "installed" only after self-test, audit and a fresh-chat boot).
- Reading the person is built in, openly and with consent: the AI adapts to how they type or talk, says what it noticed, asks before saving a style card, asks (optionally) about goals and worries to design around them, and never uses a worry to steer, never diagnoses or labels, never infers protected traits. That is the kit's answer to "without leading them astray."
- One source, three outputs: `src/protocol.md` + `hub-kit.sql` + `hub_local.py` → `HUB-KIT.md` (with SHA-256 fingerprints), `hub-kit.html` (standalone page), and the artifact page (built outside the repo).

**Facts / preferences:**
- Tested: the cloud SQL on a throwaway PostgreSQL 16 cluster (self-test 23/23, audit clean, reinstall clean, anon/authenticated refused at the schema, a foreign `hub` schema left untouched); the Supabase-specific pieces probed on a real Supabase project and rolled back; the local script 23/23; and both code blocks extracted from `HUB-KIT.md` itself, fingerprints matched, installed from scratch, 23/23 each.
- A tampered kit changes the code and its printed fingerprint together, so the AI is told to read the code before running it (no network calls, nothing outside `hub` or `~/.hub`); fingerprints catch truncation.

**Artifacts:**
- `share/hub-kit/` (HUB-KIT.md, hub-kit.html, hub-kit.sql, hub_local.py, README.md, src/).
- The page "Hub Kit Installer" (private artifact; copy buttons and a save button through the platform's download prompt).

**Open threads:**
- Not yet run by a real first-time user on another AI (ChatGPT, Gemini); the first run is the real test of the teaching and the human-step blocks.

## 2026-09-26 — Hub Kit v1.1: routing, an importer, a config file

**Decisions:**
- Kit v1.1 adds what a second week of use needs: `hub.route(text)` (cloud) and `route` (local) so a plain sentence reaches the right subject and its open threads; `hub_import.py` brings what people already have (a notes folder, a ChatGPT or Claude data export, a CSV) in as raw captures, with the guard's refusals counted and never shown; `hub.config.example.json` for level, owner, surfaces and import settings, nothing secret in it. The protocol gained section 9 "bring what they already have" and appendix D.
- The importer never invents facts from old text: an AI reads the captures afterwards and writes facts with quotes, the way the kit's section 9 teaches.

**Facts / preferences:**
- Tested: the cloud SQL 24 of 24 on PostgreSQL 16, the local script 24 of 24, all four importer readers, the importer's cloud SQL file applied once and re-applied as a no-op. HUB-KIT.md is 150,345 bytes with fresh fingerprints; the artifact page is republished as version 3.

**Artifacts:**
- `share/hub-kit/hub_import.py`, `share/hub-kit/hub.config.example.json` (new); `hub-kit.sql`, `hub_local.py`, `src/protocol.md`, `src/build.py` (VERSION 1.1), `README.md`, `HUB-KIT.md`, `hub-kit.html` (updated); the "Hub Kit Installer" artifact.

**Open threads:**
- Still not run by a real first-time user on another AI; it is on the hub's backlog now, so it stays in view.
