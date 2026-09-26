# The chat report prompt

The owner pastes this into every open chat when the QC lead needs every
chat's state. Replace `<hub project>` with the hub's project name; a chat
without a hub skips step 3.

---

**QC LEAD CHECK-IN**

I'm pulling all my chats into one system. One chat is now the **QC lead**:
it reviews every change across my repos, merges pull requests, deletes
branches, and keeps the hub (my one memory for every Claude, the
`<hub project>` project) and every build consistent. Nothing you did is
being thrown away; I need your full state so the lead can fold your work
into one solid system.

Do this now, in order:

1. **Stop and secure.** Start nothing new. Don't merge, rebase or delete
   anything, and don't touch any repo but your own. If you have commits that
   are not pushed, push them to your own branch and open a draft pull
   request, but don't merge it. If you can't push, list them.
2. **Report.** Fill in the block below completely:
   - links, pull request numbers and their state (open, merged or closed)
   - branch names, file paths and artifact links
   - hub ids (raw, fact, thread and backlog ids)

   Write "none" for an empty line. Never include a secret, an account number
   or a password.
3. **Log it.** If you can reach the hub, save the report with `hub_capture`,
   titled `CHAT REPORT — <this chat's name>`, and put the id it returns on
   the `hub:` line. If you can't reach it, write `hub: not reachable`.
4. **Give me the block** as one code block, with nothing after it, so I can
   paste it to the QC lead. Then pause work in this chat until I paste the
   lead's reply here.

```
CHAT REPORT — <this chat's name>
surface: <Claude Code cloud / Claude Code on the Mac / claude.ai chat / Cowork> · date: <today>
purpose: <what this chat was for, one line>
repos touched: <owner/repo, … or none>
done: <each finished thing: what, and where (pull request, commit, file or artifact link)>
pull requests: <repo#N · title · open, merged or closed · CI state>
unfinished or unpushed: <each unfinished thing, where it lives, the exact next step>
waiting on the owner: <each thing only the owner can do, as one copy-paste prompt or command>
hub writes: <ids written, or none>
conflicts or risks: <anything that may collide with another chat, anything sensitive in the wrong place, anything broken>
gaps and ideas: <up to five, most valuable first: what is missing or weak in the hub or the build, and the fix you would make>
hub: <raw id> or not reachable
```
