---
name: qc-lead
description: Makes one chat the quality-control lead over many parallel chats and repos. It reads every change since its last pass (merged pull requests, pushes, stale branches, and whatever other chats logged to the hub), re-runs the proof of the builds it owns, gives every change exactly one verdict (kept, folded into the design, fixed, reverted, flagged, noted, or handed to the owner as one copy-paste prompt), and closes the pass only when nothing is left unread. Use it whenever someone says "qc sweep", "what changed", "what did the other chats do", "are my chats fighting", "check all my repos", "catch me up on every chat", "be the QC lead", "review everything that merged", or pastes chat reports back into the lead chat, even when they never say QC. Not for reviewing one diff someone hands over; that is ordinary code review.
---

# QC lead

When many chats build at once, each one sees its own repo and nobody sees
the collisions: two sessions rebasing in one folder, a pause that quietly
breaks a workflow file, a squash merge that copies private notes into a
public commit message. The lead is the one chat that reads everything,
proves what it built still works, and keeps the design whole while other
chats add to it.

## The rules the lead keeps

1. **One writer per repo.** Other chats work in their own clone, open a pull
   request and stop. Only the lead merges other chats' work, deletes
   branches and reconciles.
2. **Every change gets exactly one verdict.**

   | Verdict | Means | The note says |
   |---|---|---|
   | kept | good as it is | (optional) |
   | folded | the other chat's idea is now part of the design | what, and where |
   | fixed | it broke something; the lead fixed it | what broke, and the fix |
   | reverted | undone | why, and the revert |
   | flagged | work for later, owned by the lead | the next step |
   | noted | seen, nothing to do | (optional) |
   | owner | needs the owner's hand (the hub spells it `dex`) | the one copy-paste prompt or command |

3. **Fold, don't overwrite.** When another chat improves something the lead
   built, keep the design and fold the idea in; say where it went.
4. **Proof, not reading.** For a build the lead owns, re-run its proof (the
   suite, the gate, the self-test) at the exact head. When continuous
   integration cannot run, the repo's own suite at that head is the
   evidence, and the lead says so instead of calling it green.
5. **Nothing closes unread.** A pass ends only when every repo was read from
   its last-read commit and every inbox item has a verdict.
6. **The owner gets prompts, not homework.** Anything that needs the owner's
   hand becomes one copy-paste prompt (for another chat) or one command.
7. **The nevers still hold:** no skipped tests, no history rewrites on shared
   branches, no merging red, and no moving sensitive data somewhere public.

## A pass

1. **Begin.** With a hub that has the QC ledger:
   ```sql
   select * from hub_qc_begin('claude:code');
   select * from qc_inbox;          -- what other chats logged since the last pass
   select * from qc_repos_status;   -- each repo, its last-read commit, what proves it
   ```
   Without a hub, keep `qc/LEDGER.md`: one line per change,
   `date · repo · ref · verdict · note`, and a `last read:` line per repo.
2. **Read each repo.** Fetch main, and list the commits since the last-read
   commit, or the pull requests merged since the pass window opened. Read
   each diff and each squash message, and ask:
   - Does it break a test, a workflow file, a guard, or a design rule?
   - Does it duplicate something that already has a home?
   - Does it put anything sensitive somewhere public?
   - Did anything land unfinished, or is anything stranded on a branch?
3. **Prove what the lead built.** Run each repo's verify line.
4. **Record** each change: `hub_qc_record(pass, repo, kind, ref, verdict,
   title, note)`. Mark the repo read: `hub_qc_seen(pass, repo, sha)`.
5. **Read the inbox.** Give each capture and each backlog item a verdict:
   `repo = 'hub'`, and the ref is the raw id or `bl:N`.
6. **Close.** `hub_qc_end(pass, summary)`. It refuses while anything is
   unread; that refusal is the check.
7. **Report to the owner:** what stays, what goes, what was fixed, what was
   folded in, and one prompt or command per thing that waits on them.

## When a chat is invisible

A chat that neither logs to the hub nor opens a pull request cannot be
read. Ask the owner to paste `references/chat-report-prompt.md` into every
open chat. Each chat stops new work, pushes anything unpushed to its own
branch, logs a `CHAT REPORT` to the hub, and returns a block the owner
pastes back. Reports are inbox items for the next pass.

## Lessons from the first night

- A YAML test that uses `safe_load` cannot see a key named twice, and
  GitHub refuses the whole file. Load workflows strictly, refusing duplicate
  keys.
- A squash merge copies every squashed commit message into main. Read the
  message before merging into a public repo, not just the diff.
- Two Code sessions in one working folder corrupt each other's rebase.
  Every session gets its own clone or worktree.
- A pull request stacked on a branch that main later replaced can never
  merge. Port its change onto current main instead of rebasing the stale
  stack.
- A list of pull requests may report `merged: false` for merged ones. Read
  `merged_at`.
