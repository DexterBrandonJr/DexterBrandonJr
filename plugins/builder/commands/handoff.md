---
description: Hand work to the other surface (Cowork to Code, or Code to Cowork) as a hub thread
---
Hand this to the other surface: $ARGUMENTS

Follow the `tandem` skill, section 3.

1. The target is `code` when the work needs a repository, a pull request, CI or a migration. It is `cowork` when the work needs Dex's Mac: its files, its apps, signed-in Chrome, or Office documents. If $ARGUMENTS names a target, use that one.
2. Write a next step that stands alone, because the other side starts cold:
   - the goal and what done looks like;
   - where the inputs are;
   - the proof expected back.

   Put no secrets, no account numbers beyond the last four, no money detail and no patient detail in it. Point at where those live instead.
3. Run `select * from hub_handoff('<target>', '<title>', '<next step>', '<subject or null>', 'claude:<this surface>')`. Check that the result reads `new thread`. If it reads `already-open`, a thread with that title exists and only its next step changed. To move that thread to the other surface, close it first and hand it off again (see `tandem` section 3).
4. Reply in two lines:
   - `Handed to <Target> as t:<id>: <title>`
   - the line Dex pastes to start it now: `/builder:pickup t:<id>`
