-- 0022_coach_fix2: second QA/QC pass on the model coaching system.
--
-- Found live, all still true after 0021's fix to coach_analyze_and_advise():
--
-- 1. coach_runs had no builder_id column. Runs carried session_id/chat_id
--    only, so no run could ever be attributed back to a person across
--    sessions -- there was no query that could answer "which model does
--    dex actually use most, and how often does it succeed for him."
-- 2. coach_log_run()'s only per-builder write was "last value wins":
--    favorite_model was overwritten, unconditionally, to whichever model
--    was JUST logged -- not the most-used one. Despite the name, it never
--    represented a favorite.
-- 3. The same insert wrote p_task_type (e.g. "coding") into the `phase`
--    column, which is documented as "build, test, debug, fix" -- task
--    type and build phase were conflated, and phase was never updated
--    again after the first call for a given builder_id.
-- 4. coach_recommend()'s alternative_model / alternative_effort columns
--    were hardcoded to null -- the "runner-up" this schema's own doc
--    comments and models.json's secondary-model fields promise was never
--    computed.
--
-- Fixed here: builder_id added to coach_runs; coach_log_run() takes an
-- explicit p_phase (no longer conflated with task_type) and now computes
-- favorite_model / reliable_effort / common_task_types as real aggregates
-- over that builder's logged runs; coach_recommend() returns the
-- second-highest-confidence row for the same task_type as the runner-up.
--
-- Explicitly NOT fixed here (flagged, needs a product decision, not a bug
-- fix): coach_lessons and coach_runs.builder_lesson are still never
-- written by any function -- "lessons learned" remains schema only, since
-- what qualifies as a lesson and who writes one is a design choice, not
-- an obvious code fix. known_constraints, prefers_speed, prefers_accuracy,
-- cost_per_week_usd, last_phase_run and last_model_switch remain
-- unpopulated placeholders for the same reason.

alter table coach_runs add column if not exists builder_id text;
create index if not exists coach_runs_builder_id on coach_runs(builder_id);

drop function if exists coach_log_run(text,text,text,text,text,integer,integer,numeric,integer,text,text,text);

create function coach_log_run(
  p_surface text,
  p_model_id text,
  p_effort text,
  p_task_type text,
  p_success_status text,
  p_input_tokens integer default null,
  p_output_tokens integer default null,
  p_cost_usd numeric default null,
  p_duration_seconds integer default null,
  p_notes text default null,
  p_session_id text default null,
  p_builder_id text default null,
  p_phase text default null
)
returns bigint language plpgsql volatile set search_path = public as $$
declare
  v_run_id bigint;
  v_favorite_model text;
  v_reliable_effort text;
  v_common_task_types text[];
begin
  insert into coach_runs (
    surface, session_id, model_id, effort, task_type,
    success_status, input_tokens, output_tokens,
    cost_usd, duration_seconds, notes, builder_id
  ) values (
    p_surface, p_session_id, p_model_id, p_effort, p_task_type,
    p_success_status, p_input_tokens, p_output_tokens,
    p_cost_usd, p_duration_seconds, p_notes, p_builder_id
  )
  returning id into v_run_id;

  if p_builder_id is not null then
    -- real aggregates over this builder's actual run history, in place
    -- of "whichever value happened to be logged most recently"
    select cr.model_id into v_favorite_model
    from coach_runs cr where cr.builder_id = p_builder_id
    group by cr.model_id order by count(*) desc limit 1;

    select cr.effort into v_reliable_effort
    from coach_runs cr
    where cr.builder_id = p_builder_id and cr.success_status = 'succeeded'
    group by cr.effort order by count(*) desc limit 1;

    select array_agg(t.task_type order by t.cnt desc) into v_common_task_types
    from (
      select cr.task_type, count(*) as cnt from coach_runs cr
      where cr.builder_id = p_builder_id
      group by cr.task_type order by count(*) desc limit 5
    ) t;

    insert into coach_builder_profile (
      builder_id, phase, favorite_model, reliable_effort, common_task_types,
      total_runs, total_cost_usd, updated_at
    ) values (
      p_builder_id, p_phase, v_favorite_model, v_reliable_effort, v_common_task_types,
      1, coalesce(p_cost_usd, 0), now()
    )
    on conflict (builder_id) do update set
      phase = coalesce(p_phase, coach_builder_profile.phase),
      favorite_model = v_favorite_model,
      reliable_effort = v_reliable_effort,
      common_task_types = v_common_task_types,
      total_runs = coach_builder_profile.total_runs + 1,
      total_cost_usd = coach_builder_profile.total_cost_usd + coalesce(p_cost_usd, 0),
      updated_at = now();
  end if;

  perform hub_log(p_surface, 'coach-run', jsonb_build_object(
    'model', p_model_id,
    'effort', p_effort,
    'task_type', p_task_type,
    'success', p_success_status,
    'tokens_input', p_input_tokens,
    'tokens_output', p_output_tokens,
    'cost_usd', p_cost_usd
  ));

  return v_run_id;
end $$;

revoke execute on function coach_log_run(text,text,text,text,text,integer,integer,numeric,integer,text,text,text,text) from public, anon, authenticated;

-- coach_recommend(): fill in the runner-up instead of hardcoded nulls
drop function if exists coach_recommend(text,text);

create function coach_recommend(p_task_type text, p_builder_id text default null)
returns table (
  model_id text,
  model_name text,
  effort text,
  confidence numeric,
  rationale text,
  alternative_model text,
  alternative_effort text
) language plpgsql stable set search_path = public as $$
declare v_builder_phase text;
begin
  if p_builder_id is not null then
    select phase into v_builder_phase from coach_builder_profile where builder_id = p_builder_id;
  end if;

  return query
  with ranked as (
    select
      a.model_id, m.name, a.recommended_effort, a.confidence, a.rationale,
      row_number() over (order by a.confidence desc) as rn
    from coach_advice a
    join coach_models m on a.model_id = m.model_id
    where a.task_type = p_task_type
      and a.confidence >= 0.70
  )
  select
    top.model_id, top.name, top.recommended_effort, top.confidence, top.rationale,
    alt.model_id, alt.recommended_effort
  from ranked top
  left join ranked alt on alt.rn = 2
  where top.rn = 1;
end $$;

revoke execute on function coach_recommend(text,text) from public, anon, authenticated;

-- self-test: exercise builder_id aggregation and the runner-up field
create or replace function _hub_selftest_coach() returns integer
language plpgsql volatile set search_path = public as $$
declare v_run_id bigint; v_advice record; v_runs integer;
begin
  select coach_log_run('chat', 'claude-haiku-4-5-20251001', 'high', '_qc_coach_selftest', 'succeeded',
                       5000, 2000, 0.015, 30, 'Haiku handled quick fix', null, '_qc_builder', 'build') into v_run_id;
  if v_run_id is null then raise exception 'FAIL C1 coach_log_run returned null'; end if;

  select * into v_advice from coach_recommend('_qc_coach_selftest');
  if v_advice is not null then raise exception 'FAIL C2 expected no advice before runs'; end if;

  for v_runs in 1 .. 6 loop
    perform coach_log_run('chat', 'claude-sonnet-5', 'medium', '_qc_coach_selftest', 'succeeded',
                          8000, 3000, 0.045, 45, 'Sonnet coding run ' || v_runs, null, '_qc_builder', 'build');
  end loop;

  perform coach_analyze_and_advise('_qc_coach_selftest');

  select * into v_advice from coach_recommend('_qc_coach_selftest');
  if v_advice is null then raise exception 'FAIL C3 analysis did not generate advice after 5+ runs'; end if;

  -- C4: builder_id aggregation actually attributes runs and computes a
  -- real favorite (sonnet, 6 runs) over the noise of one haiku run
  if (select favorite_model from coach_builder_profile where builder_id = '_qc_builder') <> 'claude-sonnet-5' then
    raise exception 'FAIL C4 favorite_model was not computed from run frequency';
  end if;

  -- clean up: this self-test's rows are not real data
  delete from coach_advice where task_type = '_qc_coach_selftest';
  delete from coach_runs where task_type = '_qc_coach_selftest';
  delete from coach_builder_profile where builder_id = '_qc_builder';

  return 4;
end $$;

revoke execute on function _hub_selftest_coach() from public, anon, authenticated;

select hub_migrated('0022_coach_fix2');
