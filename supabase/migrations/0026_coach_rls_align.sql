-- 0026_coach_rls_align: match the coaching tables to the hub's row-level
-- security convention.
--
-- Every other table in the hub has row-level security enabled and no
-- policy: for any role but the owner that is deny-all, and the hub grants
-- no table access to anon or authenticated in any case. 0020 gave the six
-- coaching tables a permissive `select using (true)` policy each -- the
-- only permissive policies in the database (pg_policies, 2026-09-27).
-- Harmless today because the grants are revoked; still the one place a
-- future `grant select` would expose rows at once. The `insert with check
-- (false)` policies were no-ops for the same reason. All twelve go.
-- Row-level security stays enabled, as everywhere else.

drop policy if exists coach_models_read on coach_models;
drop policy if exists coach_models_write on coach_models;
drop policy if exists coach_effort_read on coach_effort;
drop policy if exists coach_effort_write on coach_effort;
drop policy if exists coach_advice_read on coach_advice;
drop policy if exists coach_advice_write on coach_advice;
drop policy if exists coach_runs_read on coach_runs;
drop policy if exists coach_runs_write on coach_runs;
drop policy if exists coach_lessons_read on coach_lessons;
drop policy if exists coach_lessons_write on coach_lessons;
drop policy if exists coach_builder_profile_read on coach_builder_profile;
drop policy if exists coach_builder_profile_write on coach_builder_profile;

select hub_migrated('0026_coach_rls_align');
