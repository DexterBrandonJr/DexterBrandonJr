# Memory File Schema

Exact formats `scripts/new_entry.py` and `scripts/search_memory.py` rely on. Hand-editing memory files is fine as long as the result still matches this shape — the scripts parse it with simple line patterns, not a real markdown parser, so drifting from it silently breaks indexing and search.

## `INDEX.md`

One line per topic, sorted by most-recently-updated first:

```
- [<title>](topics/<slug>.md) — updated <YYYY-MM-DD> — <one-line summary of what's in it>
```

Example:

```
- [Q3 pricing revamp](topics/q3-pricing-revamp.md) — updated 2026-08-14 — decisions on the new tier structure and open questions for legal
- [Dexter's writing voice](topics/dexters-writing-voice.md) — updated 2026-07-02 — tone/style preferences for blog drafts
```

The one-line summary is what recall scans first — write it as the thing you'd want to see to know whether to open the file, not a restatement of the title.

## `topics/<slug>.md`

```markdown
# <Title>

<optional one-paragraph standing summary of this topic, kept current as entries accumulate>

## <YYYY-MM-DD> — <short entry title>

**Decisions:** ...
**Facts / preferences:** ...
**Artifacts:** ...
**Open threads:** ...

## <YYYY-MM-DD> — <next entry, newest last>
...
```

Newest entries go at the bottom (chronological), so a reader scanning top-to-bottom gets the history in order. Omit any of the four fields in an entry that has nothing for it — don't write "None" placeholders.

`<slug>` is lowercase, hyphenated, derived from the title (`Q3 pricing revamp` → `q3-pricing-revamp`).

## `raw/<YYYY-MM-DD>.md`

No fixed internal structure required beyond a date-stamped filename — this is the escape hatch for verbatim content the user explicitly asked to keep, not something recall reads by default. If you do write one, at least label which topic(s) it relates to at the top so search can connect it back:

```markdown
<!-- topics: q3-pricing-revamp -->

(verbatim content)
```
