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
