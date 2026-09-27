# Model Coaching System

## 2026-09-27 — Phase 1 build: docs/MODELS.md, models.json, migration 0020_coach

**Decisions:**
- Build in four phases (build untested → test → debug with Fable → fix & ship). Phase 1 on Haiku 4.5 as requested for training.
- Three core deliverables: guide (docs), catalog (JSON), database schema (migration 0020). No external validation until Phase 3 (debug).
- Every model invocation logged to hub with model, effort, task type, success status, tokens, cost. Recommendations generated from 5+ runs per combo.
- Builder profile learned over time: favorite model, reliable effort, common task types, cost trajectory. Feeds into proactive coaching.

**Facts / preferences:**
- Phase 1 complete: untested code committed to `claude/skill-builder-chat-lui7sz`, pushed, draft PR #44 created
- Research phase collected comprehensive data: 5 Claude models (Fable 5.1 thru Haiku 4.5), effort mechanics, pricing per plan, use-case matrix, phased-build alignment
- Coaching schema (0020): coach_models, coach_effort, coach_runs, coach_advice, coach_lessons, coach_builder_profile tables + APIs
- check-in scheduled every ~60min via send_later until PR done (merged or closed)
- Draft PR does not block; no CI configured for this repo; no tests run on commit; Phase 1 = build only

**Artifacts:**
- PR #44: https://github.com/DexterBrandonJr/DexterBrandonJr/pull/44 (draft, untested)
- Commit 0e95c37: "Build phase 1 (untested): model coaching system"
- docs/MODELS.md: 270-line guide (availability, effort, use-case matrix, pricing, phased-build per phase, tuning by task type)
- models.json: machine-readable catalog with all model metadata, effort defs, recommendations, coaching fields
- migration 0020_coach.sql: schema + coach_recommend(), coach_log_run(), coach_analyze_and_advise() APIs + selftest

**Open threads:**
- Phase 2 (Test): Will Supabase apply 0020 cleanly? Does hub_selftest pass on the new tables?
- Phase 3 (Debug): Any logic errors in coach_analyze_and_advise()? Does confidence calculation make sense for the task types?
- Phase 4 (Fix): Integrate with Hub Kit generic coaching section; add to skill phrases; capture this chat's builder profile to the hub
- Builder profile capture: Need to log this session's decisions, model choices, task types as a pattern for future chats to learn from
