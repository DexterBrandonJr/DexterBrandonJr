-- 0021_coach_fix: repair coach_analyze_and_advise(), the learning core of
-- the model coaching system (0020_coach), which never actually worked.
--
-- Found under QA/QC after 0020 shipped and was reported (wrongly) as fully
-- tested:
--
-- 1. coach_analyze_and_advise() declared `returns table (task_type text,
--    ...)`, which makes `task_type` a PL/pgSQL variable in scope for the
--    whole function body -- not just in SELECT/WHERE clauses but also in
--    an INSERT's column list and an ON CONFLICT target list. Every bare
--    `task_type` reference throughout the function collided with it, so
--    every call raised "column reference task_type is ambiguous." The
--    fix renames the OUT column to `queried_task_type`, which requires
--    DROP FUNCTION first (Postgres does not allow CREATE OR REPLACE to
--    change OUT-parameter names).
-- 2. Its `on conflict (task_type, model_id)` clause had no backing unique
--    constraint on coach_advice, so even a fixed function body would still
--    fail at the insert.
-- 3. _hub_selftest_coach(), defined in 0020_coach.sql, was never actually
--    installed on the live hub -- confirmed by querying pg_proc. The
--    "Selftest: PASS (94 checks)" claim in PR #44 was the pre-existing
--    suite; the coaching self-test silently never ran. It is (re)installed
--    here and now contributes 3 checks, bringing hub_selftest() to 97.
--
-- Also fixes the "best effort" pick, which previously chose an arbitrary
-- effort level among ties on a boolean sort key instead of the one with
-- the actual highest success rate.
--
-- Also: the coach_builder_profile row this session logged in the prior
-- migration used a session-scoped builder_id (session_...), which would
-- have fragmented the "learned patterns in how Dex works" profile into a
-- new, disconnected row every session. Corrected live to builder_id='dex'
-- (the hub's established identifier for him) -- no schema change needed,
-- recorded here for the audit trail.

alter table coach_advice
  add constraint coach_advice_task_model_uniq unique (task_type, model_id);

drop function if exists coach_analyze_and_advise(text);

create function coach_analyze_and_advise(p_task_type text default null)
returns table (
  queried_task_type text,
  advice_count integer,
  new_lessons integer
) language plpgsql volatile set search_path = public as $$
declare
  v_task text;
  v_model text;
  v_runs integer;
  v_success_rate numeric;
  v_avg_cost numeric;
  v_avg_tokens_out integer;
  v_best_effort text;
begin
  for v_task, v_model in
    select distinct cr.task_type, cr.model_id from coach_runs cr
    where (p_task_type is null or cr.task_type = p_task_type)
      and cr.created_at > now() - interval '30 days'
  loop
    select
      count(*),
      sum(case when cr.success_status = 'succeeded' then 1 else 0 end)::numeric / count(*),
      avg(cr.cost_usd)::numeric,
      avg(cr.output_tokens)::integer
    into v_runs, v_success_rate, v_avg_cost, v_avg_tokens_out
    from coach_runs cr
    where cr.task_type = v_task and cr.model_id = v_model;

    if v_runs > 5 then
      -- the effort level with the highest success rate for this task+model,
      -- ties broken by run count (was: an arbitrary tie among booleans)
      select cr.effort into v_best_effort
      from coach_runs cr
      where cr.task_type = v_task and cr.model_id = v_model
      group by cr.effort
      order by
        sum(case when cr.success_status = 'succeeded' then 1 else 0 end)::numeric / count(*) desc,
        count(*) desc
      limit 1;

      insert into coach_advice (
        task_type, model_id, recommended_effort, confidence, rationale, based_on_runs
      ) values (
        v_task, v_model, v_best_effort, v_success_rate,
        format('%s runs, %s%% success rate, $%s avg cost', v_runs, round(v_success_rate * 100), round(v_avg_cost, 4)),
        v_runs
      )
      on conflict (task_type, model_id) do update set
        recommended_effort = excluded.recommended_effort,
        confidence = excluded.confidence,
        rationale = excluded.rationale,
        based_on_runs = excluded.based_on_runs,
        last_updated_at = now();
    end if;
  end loop;

  return query
  select
    coalesce(p_task_type, 'all'),
    (select count(*) from coach_advice ca where (p_task_type is null or ca.task_type = p_task_type))::integer,
    (select count(*) from coach_lessons cl where (p_task_type is null or cl.task_type = p_task_type))::integer;
end $$;

revoke execute on function coach_analyze_and_advise(text) from public, anon, authenticated;

-- The self-test 0020_coach.sql defined but never actually installed live.
create or replace function _hub_selftest_coach() returns integer
language plpgsql volatile set search_path = public as $$
declare v_run_id bigint; v_advice record; v_runs integer;
begin
  select coach_log_run('chat', 'claude-haiku-4-5-20251001', 'high', '_qc_coach_selftest', 'succeeded',
                       5000, 2000, 0.015, 30, 'Haiku handled quick fix') into v_run_id;
  if v_run_id is null then raise exception 'FAIL C1 coach_log_run returned null'; end if;

  select * into v_advice from coach_recommend('_qc_coach_selftest');
  if v_advice is not null then raise exception 'FAIL C2 expected no advice before runs'; end if;

  for v_runs in 1 .. 6 loop
    perform coach_log_run('chat', 'claude-sonnet-5', 'medium', '_qc_coach_selftest', 'succeeded',
                          8000, 3000, 0.045, 45, 'Sonnet coding run ' || v_runs);
  end loop;

  perform coach_analyze_and_advise('_qc_coach_selftest');

  select * into v_advice from coach_recommend('_qc_coach_selftest');
  if v_advice is null then raise exception 'FAIL C3 analysis did not generate advice after 5+ runs'; end if;

  -- clean up: this self-test's rows are not real data
  delete from coach_advice where task_type = '_qc_coach_selftest';
  delete from coach_runs where task_type = '_qc_coach_selftest';

  return 3;
end $$;

revoke execute on function _hub_selftest_coach() from public, anon, authenticated;

update coach_builder_profile set builder_id = 'dex'
where builder_id = 'session_01PCCg5xZAa7LjECtq6zXyLT'
  and not exists (select 1 from coach_builder_profile where builder_id = 'dex');

select hub_migrated('0021_coach_fix');
