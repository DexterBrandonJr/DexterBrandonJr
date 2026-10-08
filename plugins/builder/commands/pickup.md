---
description: Take a handoff addressed to this surface (t:<id>, or the oldest), do it, and close it with proof
---
Pick up: $ARGUMENTS

Follow the `tandem` skill, section 4.

1. If $ARGUMENTS names a thread (`t:12` or `12`), read that one: `select id, owner, title, next_step, due_at from threads where id = <id>`. Otherwise take the oldest open thread whose owner is `claude:<this surface>`.
2. If the thread is addressed to the other surface, or it needs something only the other surface has, hand it back with `/builder:handoff` and say why in one line.
3. Do the work to the standard in `tandem` section 6. That means building it the workhorse way, running it the phased-build way, and running the QC gate before reporting.
4. Close the thread: `select * from hub_thread_close(<id>, '<what was done, where it is, the proof>', 'claude:<this surface>')`.
5. Report the way section 6 describes, with the payload at the bottom.
