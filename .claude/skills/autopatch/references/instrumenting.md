# Instrumenting a new project for autopatch

A checklist for giving a tool the ability to report its own failures. The
working reference implementation is `src/csearch/journal.py` in
`DexterBrandonJr/macos-contextual-search`; this is the shape to copy and the
reasoning behind each part.

## 1. The journal

One newline-delimited JSON file in the tool's own data directory (not the
repository — it describes a machine, not a codebase, and it must never be
committed). Add it to `.gitignore`.

Per line:

```json
{"ts": 1757200000.0, "event": "run", "command": "index", "ok": true, "duration_ms": 812.4}
{"ts": 1757200100.0, "event": "error", "command": "search", "ok": false,
 "error_type": "OperationalError", "error_message": "no such column: dev",
 "signature": "a1b2c3d4e5f6", "context": {"python": "3.11.9"}}
```

Three properties that matter more than they look:

**Journalling must never break the tool.** Wrap every write in a bare
`except OSError: pass`. A missing diagnostic is a small loss; a command that
crashes because its logging failed is a large one.

**Rotate it.** Cap the line count and trim to the recent half when exceeded.
An append-only file nobody trims is a slow disk leak.

**Record deliberate interrupts separately, or not at all.** A user pressing
Ctrl-C is not a defect, and journalling it as one buries the real failures.

## 2. The signature

The single most important design decision. A signature groups repeated
occurrences of one bug so a report reads as "3 problems, one of them 40 times"
rather than "42 problems."

Build it from **the exception type plus the function names in the traceback.**
Then deliberately exclude two things:

- **Line numbers.** Editing an unrelated function shifts everything below it,
  and every open bug would appear to be brand new.
- **The message.** It usually embeds a path, an id, or a value that differs on
  every occurrence, so including it makes each occurrence its own "issue."

```python
frames = [f"{Path(f.filename).name}:{f.name}" for f in traceback.extract_tb(exc.__traceback__)]
payload = f"{type(exc).__name__}|{'>'.join(frames[-5:])}"
signature = hashlib.sha256(payload.encode()).hexdigest()[:12]
```

Last five frames, not all of them: the deep tail is where the bug is, while the
outer frames are usually the same dispatch scaffolding for every command.

## 3. Redaction

Assume any report will be pasted somewhere. On a personal machine the paths
*are* the sensitive part — a filename can name a client, a diagnosis, or a
legal matter, and the directory structure alone can be revealing.

Reduce paths to shape rather than removing them: `~/<4 levels>/*.pdf` keeps
what a diagnosis needs (depth, file type, that it was under home) and discards
what it does not. Apply it to whole strings, since paths appear inside error
messages, not only in dedicated fields.

Redaction on by default, `--no-redact` to opt out locally.

## 4. The report command

```
<tool> selfcheck              # human-readable
<tool> selfcheck --json       # for an agent
<tool> selfcheck --brief      # one line, silent when healthy
<tool> selfcheck --clear      # after fixes are confirmed
```

The JSON shape autopatch expects:

```json
{
  "tool": "csearch",
  "runs": {"runs": 120, "failures": 3, "failure_rate": 0.025},
  "issues": [
    {"signature": "a1b2c3d4e5f6", "error_type": "OperationalError",
     "command": "search", "count": 12,
     "first_seen": "2026-09-01 10:22", "last_seen": "2026-09-06 18:04",
     "sample_message": "no such column: dev"}
  ],
  "environment": {"python": "3.11.9", "capabilities": {"semantic search": false}}
}
```

Include `capabilities`. A large share of apparent "bugs" are really an optional
dependency that was never installed, and having that in the same report stops
an agent from patching code to fix a missing package.

## 5. The SessionStart hook

What makes it continuous instead of something to remember.

`.claude/settings.json` in the project:

```json
{
  "hooks": {
    "SessionStart": [
      {"hooks": [{"type": "command", "command": "bash .claude/hooks/session_start.sh", "timeout": 10}]}
    ]
  }
}
```

The script must:

- **Be silent when healthy.** A hook that always prints gets tuned out, and
  then it is worse than nothing — it has trained you to ignore real signal.
- **Never fail the session.** Exit 0 on every path. Guard on the tool being
  installed at all (`command -v`), since a fresh clone will not have it.
- **Be fast.** It reads one local file. Nothing on the network, no indexing.

## Common mistakes

- Committing the journal. It describes a personal machine.
- Putting line numbers in the signature, so every edit resets every bug.
- A hook that prints a summary on every session, healthy or not.
- Logging deliberate interrupts as errors.
- Sending reports anywhere automatically. The user decides what leaves the
  machine, every time.
