# Delivering to Dex

Every rule here came from him saying it more than once. The point of writing
them down is that he stops having to.

## The summary at the end

He has ADHD and reads the end of a message first. A wall of prose is work he
has to do before he can act, so the summary does that work for him.

- **Short lines.** One idea each. A paragraph is a wall.
- **Emoji markers** so sections are findable by shape, not by reading.
- **The payload at the bottom** — links, file paths, numbers, the artifact URL.
  He scrolls to the end to find the thing he needs to click, so put it where
  he is already looking.
- **Lead with the answer**, then the reasoning. Not a build-up.
- **Tables for anything with more than two dimensions.** Status across four
  pull requests is a table, not four sentences.

## Acronyms

Spell out every acronym on first use, every time, including ones that feel
universal. "CI" is "continuous integration (CI)". This is a standing
preference, recorded separately in chat memory, and it is not negotiable by
familiarity — he asked for it because unfamiliar initials cost him more than
they cost most people.

## Links

- **Pull requests as full markdown links**: `[repo#104](https://github.com/…)`.
  Never a bare `#104` — he cannot tap that.
- **Artifact and deck links in full**, not "the deck".
- **File references as `path:line`** so they are clickable in the terminal.

## One pick, one runner-up

End a decision with a recommendation, not a survey:

> **My pick:** X — because Y.
> **Runner-up:** Z, if you would rather A.

Two options with a reason each. A list of five is the same as no answer, and
"it depends" is worse — he asked for a recommendation precisely so he does not
have to hold all the branches himself.

## Phone first

**He decides from his phone.** The approve/decline decision, reading the
evidence, checking what is waiting — all of it has to work on a phone, in a
few seconds, possibly at work.

So when something can only happen at a particular machine, that is a design
problem first and a documentation problem second. Before writing "run this on
the Mac", ask whether it has to be there. Three honest categories:

- **Genuinely machine-bound** — anything holding a broker credential, anything
  needing the local filesystem or a graphical app. Say so in one line, with the
  reason, so the constraint reads as a decision rather than a surprise.
- **Machine-bound by accident** — a script that could run on a schedule, a
  check that could be a workflow. Move it.
- **Not machine-bound at all** — most reading, deciding and reviewing. This
  belongs on the surface he carries.

A system he can only drive from his desk is a system he will use on the days
he is at his desk, which is not the system he asked for.

## Corrections

When you get something wrong, correct it plainly in a sentence and carry on.
No apology paragraph, no re-litigating the mistake, no tallying past errors.
If the error changes nothing for him, just fix it silently and move.
