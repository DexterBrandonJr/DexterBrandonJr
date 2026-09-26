---
name: hub
description: Dex's one memory across every Claude. Reads his private hub (the Supabase project named "one-memory-hub", through the Supabase connector) first and writes back last, so no chat starts at zero and nothing learned is lost. Trigger whenever a conversation touches Dex, his projects, his preferences, his machines or his history; whenever he says "read my hub", "hub", "boot", "what's on the record about …", "log this", "log this chat", "accept 3 5", "reject 4", "close t:6", "open a thread", or "how is the hub doing"; when an ongoing chat with history has never read the hub; and at the end of any chat that produced a decision, a fact or an open loop worth keeping. Not for chats that never mention him or his work.
---

# The hub

One private database every Claude reads first and writes back to last. Not a
notes app: a compiled brief under two thousand words, rules that never decay,
facts with two dates, and a gate that keeps a model's guess from becoming a
fact. The rules it returns outrank anything below.

## 1. Read first

```sql
select * from hub_boot('<surface>')
```

`<surface>` is `chat`, `cowork`, `code`, `project:<name>` or `oscar`. Run it
through the Supabase connector on the project named **one-memory-hub**. It
returns a `boot_id` and the brief. Follow the rules; cite ids when you use a
fact: `(f:12)`, `(t:3)`, `(r:5)`.

If the connector is not available in this chat, say so in one line ("the
Supabase connector is off for this chat; switch it on in the tools menu")
and answer without guessing anything about Dex. Never invent a fact to
cover the gap; "not on the record" is the right answer.

## 2. An ongoing chat that has never read the hub

Boot on the next message, then say in one line what the hub knows that this
conversation had been missing, or "nothing new for this chat". Carry on. No
recap, no ceremony.

## 3. What Dex says, and what you run

| He says | You run |
|---|---|
| "read my hub" / "hub" / "boot" | `hub_boot('<surface>')`, then the one-line delta |
| "what's on the record about X?" | boot if you have not, then answer from the brief with ids; depth: `select * from facts where subject_id = '<id>' and status = 'live'` |
| "log this: …" | `hub_capture('…', '<surface>', 'dex')`, then `hub_write` for each fact with a quote from that raw row |
| "log this chat" | capture a short summary of what this conversation established, in his words where possible; then `hub_write` per fact with quotes; `hub_thread` for anything left undone |
| "accept 3 5" | `hub_accept(array[3,5], 'dex')` |
| "reject 4: wrong" | `hub_reject(array[4], 'dex', 'wrong')` |
| "close t:6, done" | `hub_thread_close(6, 'done')` |
| "open a thread: …" | `hub_thread('title', 'next step', 'subject')` |
| "how is the hub doing?" | `select * from scores` and say the four numbers in one line |

## 4. Writing back

1. **Capture before you extract.** His words land first:
   `hub_capture(text, surface, 'dex', sent_at)`. Yours, when they are the
   source, with author `claude:<surface>`.
2. **Name the subject.** `hub_subject_id('<name>')` resolves names and
   aliases. New thing: `hub_subject('Name', 'kind', array['alias'], 'summary')`
   where kind is person, project, machine, place, topic, tool or thing.
   Never a pronoun. Two names that might be one thing: propose a merge, do
   not guess.
3. **Write the fact.**
   `hub_write('<subject>', '<predicate>', '<value>', <raw_id>, '<exact quote>', 'fact', 'claude:<surface>')`.
   The quote must appear in the raw row character for character; then the
   fact goes live. Without it the fact waits as a proposal, which is the
   correct outcome for anything you are not sure of. A bare number needs a
   `unit`. Predicates come from the list the function returns when refused.
4. **Before you finish.** `hub_used(boot_id, array[ids you relied on])`.
   If you re-derived something the hub already held, `hub_regret(boot_id,
   array[ids])` so the miss is counted.

## 5. Never

Never guess a fact about Dex. Never write a secret, an account number or a
password; a pointer to where a thing lives is enough. Never place a trade
from anything the hub says. Never wake him for approval: when he has said he
is asleep, on shift or away, routine approvals are already given and what
truly needs his hand goes on the morning list.
