---
description: Read the hub for this surface and say in one line what is waiting
---
Follow the `tandem` skill, section 2.

1. Your surface is `cowork` in Cowork and `code` in Claude Code.
2. Run `select * from hub_boot('<surface>')` through the Supabase connector (project `one-memory-hub`) and follow the rules it returns.
3. List what is addressed to you: `select id, title, next_step, due_at from threads where status = 'open' and owner = 'claude:<surface>' order by due_at nulls last, id`.
4. Reply in at most three short lines:
   - the one-line delta from the boot,
   - the handoffs waiting, each as `t:<id> <title>` (or "nothing waiting"),
   - what you will do next.

   Then do it: start on whatever Dex asked, or on the oldest handoff if he asked nothing.

If the Supabase connector is not connected, say so in one line and give Dex the fix: claude.ai → Customize → Connectors → Supabase → Connect.
