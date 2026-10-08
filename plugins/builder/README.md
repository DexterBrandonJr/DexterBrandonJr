# Builder

One builder across Cowork and Claude Code. Install it once on the claude.ai
account and both surfaces build the same way, from the same memory, behind
the same guard. Cowork reads plugins from the account and never a repo's
`.claude/` folder, so without this it starts each task without Dex's skills.

## What it adds

| Piece | What it does |
|---|---|
| `tandem` skill | Which surface does what, how work crosses between them as a hub thread, the lines that never move, and how a finished thing is handed to Dex |
| `hub` skill | The one memory every Claude reads first and writes back to last |
| `workhorse`, `phased-build`, `innovation-brief`, `scenarios` skills | How Dex's systems are built and run, briefed and stress-tested |
| `/builder:boot` | Reads the hub for this surface and lists the handoffs waiting |
| `/builder:handoff` | Hands work to the other surface as a hub thread and returns the one line to paste |
| `/builder:pickup` | Takes a handoff, does it and closes it with proof |
| `/builder:qc` and the `qc-reviewer` agent | The quality-control (QC) gate before Dex sees anything |
| Guard hook | Refuses live-trading switches, broker order tools and the live account map in every session, whatever the conversation says |
| Session-start hook | One line telling each session to boot the hub first |

## Use it

Add the marketplace `DexterBrandonJr/DexterBrandonJr` under **Customize >
Plugins > Add marketplace** and install **Builder**. In a Cowork session, type
`/builder:boot`. To move work to the other surface, type
`/builder:handoff <what>`. On the other side, paste the `/builder:pickup t:<id>`
line it returns.

## Data

The plugin sends nothing anywhere itself. The skills tell Claude to read and
write Dex's hub through the Supabase connector already on the account. The
hooks run locally and read only the tool call they judge.

## Maintaining it

The skills and the guard are copies of the canonical files in this repo's
`.claude/`, made by `python3 plugins/build.py`. That command also raises the
version, so Cowork's **Check for updates** sees the change. Edit the
originals, never the copies; `python3 plugins/tests/test_builder.py` fails
when they drift.
