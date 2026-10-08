# The Builder project in Cowork

Cowork is Claude on Dex's Mac. It handles his files, his apps, Chrome with
his sign-ins, and Office documents. Claude Code handles repositories, pull
requests and CI, and it is the quality-control (QC) lead. The **Builder**
project makes Cowork build the way the Code chat does, from the same memory
(the hub), and hands work across in both directions. It needs two installs
and a project, about ten minutes on the Mac.

Why a plugin and not just instructions: Cowork loads skills, hooks and
commands from the claude.ai account (**Customize**), never from a repo's
`.claude/` folder. The `builder` plugin (`plugins/builder/`) packages this
repo's skills and the never-lines guard for the account. A plugin on the
account also syncs into Claude Code at the next session start, so both
surfaces run the same guard.

## 1. Install the plugin

1. Update Claude Desktop (menu **Claude > Check for Updates**).
2. Open **Customize > Plugins > Add marketplace** and enter
   `DexterBrandonJr/DexterBrandonJr`.
3. Install **Builder**, then turn on **Sync automatically** for that
   marketplace so every merged change reaches the Mac.

If the marketplace will not add, use the fallback:
- Download
  `https://github.com/DexterBrandonJr/DexterBrandonJr/raw/main/plugins/builder.zip`.
- Go to **Customize > Plugins > Add > Upload plugin**.
- With this route, updates are manual.
- `python3 plugins/build.py` rebuilds the zip with every change, and the
  test fails if it is stale.

## 2. Check the connectors

Under **Customize > Connectors**:

- **Supabase**: connected. This is how every surface reads the hub.
- **Google Drive**: connected. Files cross between Cowork and Code this way.
- **GitHub**: connected, so Cowork can read repositories.
- **Webull**: open it and switch off every `place_*` tool and
  `revoke_instruction`. The guard refuses them anyway. Off is a second lock
  that does not depend on the plugin loading.

## 3. Create the project

**Projects > + > Start from scratch**, then fill in:

| Field | Value |
|---|---|
| Name | `Builder` |
| Description | the block below. Dispatch reads it to decide which project gets a task |
| Folders | a new `~/Builder` for deliverables, plus any folder the work lives in (the ER:ESO folder, the Duncan Chapel folder) |
| Instructions | the block below |
| Links | `https://github.com/DexterBrandonJr/DexterBrandonJr`, `https://github.com/DexterBrandonJr/one-memory-hub` |

**Description**

```
Dex's builder on his Mac. Use for anything that needs this computer: local files and folders, desktop apps, Chrome with his sign-ins, Excel, PowerPoint, Word and PDF, plus research and write-ups. Coding work (repositories, pull requests, CI, migrations) belongs to Claude Code; this project hands it over through the hub.
```

**Instructions**

```
You are Dex's builder on his Mac, working in tandem with Claude Code over one memory, the hub.

Start every session with /builder:boot: hub_boot('cowork') through the Supabase connector, then the handoffs addressed to claude:cowork. Say what is waiting in one line, then work. If he asked nothing, start on the oldest handoff.

The tandem skill says which surface does what and how work crosses over. Build the workhorse way; run the work the phased-build way. Do the whole batch, never ask for approval he already gave, and never wake him. What truly needs his hand goes on the morning list as one copy-paste prompt.

Anything that needs a repository, a pull request, CI or a migration: do your half, then /builder:handoff code. Code cannot see this Mac, so files cross through Google Drive and text through the hub.

Lines that never move: trading stays paper; no broker orders; no money moves; never click pay, send, transfer, buy or sell; never read ~/.config/trading-engine/accounts.json. Account numbers last four only, SSNs never, money detail stays in the vault, patient detail never leaves this Mac, her data only with her recorded consent. If the guard refuses something, say what and what Dex would type himself; never work around it.

Before Dex sees anything, run /builder:qc and label every claim Proven, Tested or Expected.

Reply for his phone: short lines, emoji markers, every acronym spelled out the first time, one recommendation with the runner-up named, and the payload (links, paths, numbers, the one copy-paste prompt) at the bottom.

Before the session ends, write back to the hub: hub_capture, then hub_writes, author claude:cowork.
```

## 4. Prove it works (first session in Builder)

Paste these one at a time into a new task in the project.

| Paste | What should happen | What it proves |
|---|---|---|
| `/builder:boot` | One line from the hub, then the waiting handoffs, at least `t:1106` (the ER equipment map) | The plugin, the Supabase connector and the hub |
| `Run this in the shell: export WEBULL_ENV=live` | Refused, with a reason that cites bl:443 | The guard hook runs in Cowork |
| `/builder:handoff code: reply that tandem works, then close the thread` | `Handed to Code as t:<id>` and a `/builder:pickup` line | A handoff reaches Code |

Paste the `/builder:pickup t:<id>` line into any Claude Code session. Code
closes it, and the next `/builder:boot` in Cowork no longer lists it.

If the second row runs instead of being refused:
- The hook did not load.
- Say so in the Code chat; it is the first thing to fix.
- The Webull switch-off from step 2 still holds in the meantime.

## 5. Let it run on its own (optional)

In a Builder task, type `/schedule` and create:

- **Weekdays 07:10, "Pick up handoffs"**: `/builder:boot, then /builder:pickup the oldest handoff if there is one; if nothing is waiting, end without a message.`

From the phone, **Dispatch** routes a task by the project description:
knowledge work lands in Builder, and coding work goes to Claude Code.

## How the two sides split work

| Work | Goes to |
|---|---|
| Mac files and folders, apps, signed-in sites, Office files | Cowork (Builder) |
| Repositories, pull requests, CI, hub migrations, merges, QC | Claude Code |
| A task with both halves | each side does its half; the handoff carries the rest |

The full working agreement is the `tandem` skill
(`.claude/skills/tandem/SKILL.md`).

## What is not verified yet

- **Hooks inside Cowork's sandbox:** the guard is Tested in Claude Code and
  under Cowork's shell tool name. The first-run check in section 4 is what
  proves it in Cowork itself.
- **A private marketplace:** this repo is public, which avoids a reported
  bug where Cowork failed to add private GitHub marketplaces. Everything in
  the plugin was already public here.
- **Where Cowork projects live:** Anthropic's two pages disagree. The
  developer docs say a Cowork project lives on the Mac only. The help center
  says one created from scratch is saved to the account. Treat it as
  Mac-only until seen otherwise.
