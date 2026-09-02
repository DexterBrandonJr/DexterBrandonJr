# Description Formulas

The description is the only field Claude reads *before* deciding whether to open a skill at all. It has to do two jobs in one or two sentences: say what the skill produces, and say — concretely — when to reach for it. Most weak descriptions do only the first job.

## The formula

```
[What it does, one clause]. [When to use it — concrete triggers, phrasings, and contexts, stated pushily enough to overcome Claude's default bias toward just answering directly].
```

The second clause is the one that's usually missing or too soft. Claude only opens a skill when it judges the task genuinely benefits from specialized handling — a simple one-step request often gets handled directly even with a perfectly matching skill sitting right there, because directly answering is the path of least resistance. Your description has to tip that judgment call, which means naming the scenarios explicitly rather than trusting Claude to infer them from a tidy summary.

## Before / after

**Before:** `Helps build dashboards to display data.`
Reads as a capability blurb. Doesn't say what kind of data, what "dashboard" means here, or why this beats just writing a chart inline.

**After:** `Builds fast, simple dashboards for displaying internal metrics and company data. Use this whenever the user mentions dashboards, data visualization, internal metrics, or wants to display any kind of company data — even if they don't explicitly say "dashboard."`
Names the domain, and explicitly pre-empts the case where the user's phrasing doesn't contain the obvious keyword.

**Before:** `Use for working with Excel files.`
Too broad — "working with Excel files" could mean reading, writing, charting, or converting, and gives Claude no reason to prefer this skill over just opening the file with a library inline.

**After:** `Reads, edits, and creates .xlsx/.xlsm/.csv spreadsheets — adding formulas, fixing malformed or messy tabular data, computing derived columns, applying formatting, building charts. Trigger whenever the user references a spreadsheet by name or extension and wants something done to it, even casually ("the xlsx in my downloads"), or wants tabular output delivered as a spreadsheet file.`
Enumerates the concrete operations and the casual ways people actually ask, and clarifies the boundary (deliverable must be a spreadsheet, not just "involves a table somewhere").

**Before:** `Helps with PDFs.`
No boundary at all — competes with every other skill that might touch a PDF as an input.

**After:** `Reads, merges, splits, rotates, watermarks, fills forms in, and OCRs PDF files. Use whenever a .pdf file is mentioned as input or requested as output, including extracting text/tables for use elsewhere.`

## Calibration: pushy, but not indiscriminate

"Pushy" means *specific and confident about the scenarios that are genuinely this skill's territory* — not maximally broad. Over-widen a description ("use this for anything involving documents") and it starts stealing triggers meant for sibling skills, silently, with no error to tell you it happened. The fix isn't to soften the language; it's to narrow the *territory* while keeping the confident tone within it. Push hard on the boundary that's actually yours.

Two symptoms of a too-broad description:
- It would also plausibly match a request that belongs to a different skill you (or your team) maintain.
- Removing the specific nouns and keeping only the verbs still describes something true (a sign it's describing a generic capability rather than this skill's niche).

## The cold-read self-test

Read only the `name` and `description` — nothing else in the file, no memory of this conversation — and ask: *would a stranger know precisely which real user messages should make Claude reach for this, and which shouldn't?* If the honest answer involves "well, it depends on the body," the description hasn't done its job yet; move that disambiguating detail up into the description itself.

## Common failure patterns

- **Summary instead of trigger.** Describes the output ("Generates commit messages") without saying when Claude should generate one unprompted vs. wait to be asked.
- **Generic verbs.** "Helps with," "assists with," "supports" — these describe every skill equally and distinguish none of them.
- **Buried conditions.** Trigger-relevant detail written into the body instead of the description. Claude never reads the body until it has already decided to open the skill — anything gating that decision has to live in the description.
- **Name/description mismatch.** A name implying one scope ("pdf-tools") with a description describing a narrower or different one ("only fills tax forms") — confusing for humans skimming a skill list, and a sign the two were never reconciled.
- **No negative space.** Doesn't say what's *out* of scope when the boundary is genuinely ambiguous with a sibling skill (e.g., "spreadsheet data cleanup" vs. "a chart skill that also touches spreadsheets") — a one-clause carve-out avoids two skills fighting over the same request.

## If you have the tooling for it

Eyeballing a description only catches the failures obvious enough to notice by inspection. The more rigorous version — building a real eval set of should/shouldn't-trigger prompts and iterating against measured trigger rates rather than intuition — is covered in `advanced-techniques.md` under "Tuning the trigger with evals." It catches the failures that only show up once you throw real, messy phrasings at the description instead of the clean one you wrote while you still had the whole spec in your head.
