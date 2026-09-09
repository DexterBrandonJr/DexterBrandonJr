# Pr Checkin Cadence

## 2026-09-06 — PR check-in cadence: weekly, lowest-activity day

**Decisions:** Replaced the hourly PR #6 (chat-memory backlog) check-in with a recurring weekly one, firing Thursdays 14:00 UTC (`trig_01NyZbe9wUE3CWCWBTxsyaTS`, self-bound to this session). Thursday was picked by tallying `created_at` day-of-week across ~26 recent real sessions (excluding this session's own continuous activity): Thursday had only 1 session vs. 3-7 on every other day of the week, making it the clearest low-activity day to run non-urgent monitoring on without competing with active work.
**Facts / preferences:** Dex explicitly said the hourly cadence was burning usage and asked it slowed down, then asked for weekly-on-the-slowest-day specifically, "unless i ask for you to update check-in manually" — so don't tighten this back up without being asked again, even after several quiet weekly ticks.
**Artifacts:** Old one-shot trigger `trig_0185e2VEgS4UjMNyrY8tFjyC` deleted (it was a self-bound reminder for this same session, not a cross-session ask to another party, so the disable-not-delete rule from `cross-session-trigger-hygiene.md` didn't apply). Unrelated: noticed a separate weekly Sunday check-in (`trig_01DWbo7nkZLXFKartoFn4eFw`) that the "GitHub connection troubleshooting" session set up on its own for a different PR (#7) — not touched, out of scope for this decision.
**Open threads:** If PR #6 merges or closes, this trigger should be deleted rather than left firing into a dead topic.
