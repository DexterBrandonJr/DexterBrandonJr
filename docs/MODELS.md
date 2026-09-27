# Claude models: what they are, and how this repo picks one

Two kinds of statement live here, and they are kept apart:

- **Checked** — model facts, verified on 2026-09-27 against the Claude API
  reference bundled with Claude Code (skill `claude-api`, `shared/models.md`
  and `shared/model-migration.md`). They change; re-check before quoting a
  price.
- **House defaults** — how Dex's phased builds pick a model. Judgement, not
  measurement. The coaching system (below) exists to replace them with
  numbers as runs accumulate.

Not recorded here: plan limits and what each consumer plan includes. They
change often and could not be checked against a source, so this page makes
no claim about them.

## The models (checked)

| Model | API id | Context | Max output | $ per million tokens, in / out | Notes |
|---|---|---|---|---|---|
| Fable 5.1 | `claude-fable-5-1` | 1M | 128K | 10 / 50 | Most capable widely released model. Thinking always on; effort can be set per message |
| Opus 5.5 | `claude-opus-5-5` | 1M | 128K | 4 / 20 | Successor to Opus 5 for long agentic coding. Thinking can't be turned off; effort is the control, default `medium` |
| Opus 5 | `claude-opus-5` | 1M | 128K | 5 / 25 | Full effort ladder through `max` |
| Sonnet 5 | `claude-sonnet-5` | 1M | 128K | 2 / 10 | Near-Opus quality on coding and agentic work. Effort `low`, `medium`, `high`, `xhigh`, `max` |
| Haiku 4.5 | `claude-haiku-4-5` (full id `claude-haiku-4-5-20251001`) | 200K | 64K | 1 / 5 | Fastest and cheapest. Predates adaptive thinking (models before 4.6 use `budget_tokens`); its effort support isn't stated in the reference |

**Fast mode** is a research preview on the Claude API only, for Opus 5,
Opus 5.5 and Opus 4.8, at twice the normal price (Opus 5: $10 / $50; Opus
5.5: $8 / $40). In Claude Code, `/fast` toggles it. Fable, Sonnet and Haiku
have no fast mode.

**Effort** controls how much the model thinks before answering. It changes
how many tokens a request spends, not the price per token, so its cost shows
up in the run log, not in a multiplier.

**Switching in Claude Code:** `/model <id>` (for example
`/model claude-sonnet-5`). How effort is chosen depends on the surface; on the
API it is the `effort` parameter.

## House defaults for a phased build

Dex runs builds in four phases he starts himself (skill `phased-build`).
The defaults:

| Phase | Start with | Fall back to | Why |
|---|---|---|---|
| 1 · Build (untested) | Opus 5.5, medium | Sonnet 5, high | Fast, capable output; testing comes later |
| 2 · Test | Sonnet 5 or Haiku 4.5 | Sonnet 5, higher effort | Cheap, quick loops over failures |
| 3 · Debug | Fable 5.1, high or above | Opus 5.5 | Real failures earn the most capable model |
| 4 · Fix and ship | Opus 5.5, medium | Sonnet 5, high | You know what's broken; implement and land it |

A question worth measuring, not a fact: how far down the line (Sonnet, then
Haiku) a task can go at higher effort before quality drops. That is what the
run log is for.

## The coaching system (in the hub)

Live in Dex's private hub (migrations `0020`–`0025` in `supabase/migrations/`):

- **Every run is logged** with `coach_log_run(...)`: model, effort, task
  type, outcome (`succeeded`, `needed_iteration`, `failed`, `partial`), build
  phase, and optional tokens and cost. The hub skill's write-back step says
  when: only when the model and effort are actually known.
- **Every night at 07:50 UTC** `coach_analyze_and_advise()` looks at the last
  30 days. A model with more than 5 runs on a task type gets an advice row:
  its success rate, the effort that succeeded most, average cost. Advice
  whose runs age out of the window is deleted.
- **Ask for a pick** with `coach_recommend('<task_type>')`: the best model
  and effort by success rate (at least 70%), plus a runner-up. It serves only
  advice refreshed in the last 30 days, so nothing it says is stale.
- **The profile** (`coach_builder_profile`, builder `dex`) is computed from
  the runs: most-used model, effort that succeeds most, common task types,
  current phase.

Not built yet: "lessons" (`coach_lessons`) and several profile fields
(`known_constraints`, `prefers_speed`, `prefers_accuracy`,
`cost_per_week_usd`) have no writer. They wait on a decision about what
counts as a lesson, not on code.

---

Machine-readable version: `models.json`. Last checked 2026-09-27.
