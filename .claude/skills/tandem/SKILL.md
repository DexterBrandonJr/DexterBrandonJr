---
name: tandem
description: How Cowork (on Dex's Mac) and Claude Code (repos, pull requests, CI) work as one builder over one memory, the hub. Use at the start of any Cowork session in the Builder project, whenever work belongs on the other surface ("have Code do", "have Cowork do", "hand this to", "pick up t:12", "what's waiting for me"), when a Dispatch task arrives, when a Cowork task needs a repository, a pull request or a migration, or when a Code task needs a file, an app or a signed-in site on Dex's Mac. Also use before handing Dex anything finished.
---

# Tandem: Cowork and Code as one builder

Dex builds with two Claudes. **Cowork** runs on his Mac: his files, his apps,
his signed-in Chrome, Office documents, and the scheduled jobs that need the
machine. **Claude Code** runs on repositories: code, pull requests, CI,
database migrations, and the quality-control (QC) lead that merges work.
They share one memory, the hub, and one way of building (`workhorse`,
`phased-build`). Neither waits on the other in conversation: work crosses
over as a hub thread, and Dex only ever carries one line between them.

## 1. Which surface does what

| Work | Cowork | Code |
|---|---|---|
| Files and folders on the Mac, desktop apps, Chrome with his sign-ins | **yes** | no: it cannot see the Mac |
| Excel, PowerPoint, Word, PDF made or read | **yes** | only from a repo |
| Research and write-ups for Dex to read | **yes** | yes |
| A repository: code, tests, pull requests, CI, merges | hand to Code | **yes** |
| Hub schema, Supabase migrations, GitHub Actions loops | hand to Code | **yes** |
| QC of every chat's changes | no: one lead, and it is the Code chat | **yes** |
| Something from his phone | Dispatch routes it: knowledge work to this project, coding work to Code | |

When a task has both halves (an Excel import that needs a parser in a repo),
do your half and hand the other half over in the same turn. Never stop at
"this needs the other surface".

## 2. Start of every session

1. `select * from hub_boot('<surface>')` through the Supabase connector,
   where `<surface>` is `cowork` in Cowork and `code` in Claude Code. Follow
   the rules it returns.
2. Read what is addressed to you:
   `select id, title, next_step, due_at from threads where status = 'open' and owner = 'claude:<surface>' order by due_at nulls last, id`
3. Say it in one line ("2 handoffs waiting: t:101 ER equipment map, t:1104
   Quint 24 workbook"), then do what Dex asked. If he asked nothing, start
   on the oldest handoff.

`/builder:boot` does all three.

## 3. Handing work to the other surface

```sql
select * from hub_handoff('code', '<title>', '<next step>', '<subject>', 'claude:cowork');
-- or 'cowork' ... 'claude:code' from Code
```

The next step must stand alone, because the other side starts cold:

- **the goal** in one sentence, and what done looks like;
- **where the inputs are**: a repo path, a Drive file, a hub raw id, or a
  Mac path *for Cowork to read*. Code cannot open a Mac path;
- **the proof** you expect back (a pull request, a test, a file, a number);
- **nothing sensitive**: no account numbers beyond the last four, no SSN,
  no money detail (it lives in the vault), no patient detail, no
  credentials. Point at where it lives instead.

Then tell Dex in one line, ending with the line he pastes if he wants it
started now: `/builder:pickup t:<id>`. `/builder:handoff` does this.

**Moving a thread that is already open** (one addressed to the wrong
surface): close it first, then hand it off, then read back the new id.
`hub_handoff` matches open threads by title. Given an open thread's exact
title, it only rewrites that thread's next step and keeps its owner, so a
close that follows would close the work itself. This happened on
2026-10-08 (t:101, repaired as t:1106).

**Moving files across.** Code cannot read the Mac and Cowork has no git
credentials by default. Text goes through the hub (`hub_capture`). Files go
through Google Drive, which both surfaces reach by connector. Code changes
go through a pull request, which only Code opens.

## 4. Picking work up

Read the thread, do it to the standard below, then close it with the proof:
`select * from hub_thread_close(<id>, '<what was done, where, the proof>', 'claude:<surface>')`.
If it cannot be done here, say why in one line and hand it back with
`hub_handoff`. Never leave it open and silent. `/builder:pickup` does this.

## 5. The lines that never move

These hold on both surfaces, and the plugin's guard hook enforces the first
three in code:

- **Trading stays paper.** No Claude session switches anything to live, and
  no session places, changes or revokes a broker order. Proposed trades go
  on the deck for Dex.
- **The engine never moves money.** Neither does Cowork. Computer use never
  clicks pay, send, transfer, buy or sell.
- **The live account map** (`~/.config/trading-engine/accounts.json`) is
  never read.
- **Personal data:** account numbers last four only, SSNs never, money
  detail in the vault only, patient detail never in any repo or hub row, his
  partner's data only with her recorded consent. The public repo
  `DexterBrandonJr/DexterBrandonJr` holds nothing personal.
- **Never wake him.** Approvals for routine work are already given. What
  truly needs his hand goes on the morning list as one copy-paste prompt.

If the guard refuses a call, do not look for a way around it. Say what was
refused and what Dex would type himself.

## 6. Building, and handing him the result

Build the workhorse way (`workhorse`): the record first, safety in code, a
loop, a surface he can hold, everything claimed scored. Run the work the
phased way (`phased-build`): do the whole batch, stop asking for permission
already given, and push back once at most, then build what he asked.

Before Dex sees anything, run the QC gate (`/builder:qc`):
1. run the checks the thing has;
2. open the artifact and look at it;
3. reread it as a reviewer would;
4. chase any number that does not fit;
5. say plainly what was not verified.

Label every claim **Proven** (observed), **Tested** (asserted by a check)
or **Expected** (reasoning).

End every reply the same way: short lines, emoji markers, every acronym
spelled out the first time, one recommendation with the runner-up named,
and the payload (links, paths, numbers, the one copy-paste prompt) at the
bottom. He reads it on his phone.

## 7. Write back last

Before the session ends, capture what was decided or learned:
`hub_capture` the source, then `hub_writes` one fact per row with an exact
quote. Author is `claude:<surface>`. A session that changed nothing on the
record changed nothing for the next Claude.
