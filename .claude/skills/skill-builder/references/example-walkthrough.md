# Worked Example: Weak Skill → Strong Skill

A concrete before/after, walking through every technique in `advanced-techniques.md` on one realistic case: a skill for turning a client's raw weekly sales export into a standard internal report.

## The request

> "Every Monday I get a CSV from a client with sales data in some inconsistent format, and I need to turn it into our standard report template with totals, a margin column, and a chart. Can you make this a skill?"

## Version 1 (weak)

```yaml
---
name: sales-report
description: Creates sales reports from CSV data.
---

Take the CSV the user provides and create a sales report. Calculate
totals and margins, and include a chart. Use our standard format.
Make sure to always include all the required sections and never skip
the summary. Always double check the numbers.
```

What's wrong, mapped to the techniques above:

- **Description is a summary, not a trigger** (Step 2 / `description-formulas.md`). "Creates sales reports from CSV data" doesn't say *which* CSVs, doesn't mention "client export," "Monday," or any of the phrasing the user will actually type six months from now when they've forgotten this conversation. It also doesn't distinguish this from any other CSV-touching skill.
- **No script for the deterministic 90%** (§1-2). "Calculate totals and margins" and "our standard format" are exactly the kind of one-correct-answer steps that should be a script, not re-derived from a paragraph every Monday — with the client's column names drifting slightly and Claude re-guessing the mapping each time.
- **ALL-CAPS commands with no reasoning** (§7). "Always double check the numbers" and "never skip the summary" are bare imperatives — they don't say what "double check" means operationally or why the summary matters, so they're likely to be followed inconsistently the moment the input looks unfamiliar.
- **No mention of the messy reality** — "some inconsistent format" from the request never made it in. The skill will break the first time a client renames a column.

## Version 2 (strong)

```yaml
---
name: sales-report
description: Turns a client's raw weekly sales CSV export into the standard
  internal sales report — totals, margin %, and chart, in our fixed template.
  Use this whenever the user mentions a weekly sales export, a client CSV
  with sales/revenue/cost data, or asks for "the usual report" or "this
  week's numbers" from a spreadsheet — even if they don't attach a template
  or say "report" explicitly.
---

# Sales Report Builder

## Workflow

1. Run `scripts/normalize_sales_csv.py <input.csv>`. It auto-detects
   revenue/cost/date columns across the column-naming variants we've
   seen from clients so far (listed in `references/known_formats.md`)
   and outputs a normalized CSV with fixed column names.
2. If it reports unmapped columns, use judgment: look at the sample
   values it prints and match them to revenue/cost/date/product by
   content, not just header name (clients rename columns often; the
   values themselves are the reliable signal). Re-run with
   `--map revenue=<col>,cost=<col>` once confident.
3. Run `scripts/build_report.py <normalized.csv>` to produce the
   filled template with totals, margin %, and chart — this step is
   fully deterministic once the CSV is normalized, so don't
   hand-recompute totals; if a number looks wrong, the bug is in
   step 1's mapping, not in the math.
4. Skim the output against `references/report_checklist.md` before
   handing it back — it's short, and a report missing its summary
   section is the single most common complaint we've gotten, because
   the template silently omits it when the input has fewer than two
   product categories.

## Why normalization is a separate script from report-building

Column mapping is the one genuinely judgment-requiring step (client
naming drifts, sometimes a column is ambiguous). Everything after
that — totals, margin math, chart generation, template filling — has
exactly one correct answer, so it's a script. This split means a
mapping mistake is easy to spot and fix in isolation (rerun step 1
with `--map`), instead of being buried inside one giant regenerate-
everything pass.
```

Paired with `scripts/normalize_sales_csv.py` and `scripts/build_report.py` actually existing in the skill's `scripts/` folder, and `references/known_formats.md` growing over time as new client column-naming variants get discovered.

## What changed, and why it matters at scale

- The description now fires on "this week's numbers" and "the usual report" — the actual way a busy user asks in month three, not just the clean phrasing from the first conversation where the skill was built.
- The deterministic math and template-filling moved into scripts, so the report is bit-for-bit consistent every Monday regardless of how the request was phrased that week.
- The one real judgment call (column mapping) is isolated, explained (*why* content-matching beats header-matching), and has a place to accumulate knowledge over time (`known_formats.md`) instead of being re-solved from scratch or silently wrong.
- The "never skip the summary" rule became a specific, checkable fact (*it disappears when there are fewer than two product categories*) instead of a bare imperative — which is both more likely to be caught and more informative when it fires.

This is the same shape of change worth looking for in any skill: pull the judgment calls into clearly-reasoned prose, push the one-right-answer steps into scripts, and write the description for the tired version of the user typing it from memory, not the careful version who just finished specifying the whole workflow.
