-- 0024_coach_fix4: fifth QA/QC pass on the model coaching system.
--
-- Found by replaying 0020-0023 from git onto an empty Postgres 16 and
-- testing the result, not the live hub:
--
-- 1. Advice never expired. 0023 bounded the numbers to the last 30 days,
--    but a (task, model) pair whose runs all aged out kept its advice row
--    forever, and coach_recommend() kept serving it. The same staleness
--    0023 fixed, one level up.
-- 2. Nothing ran the analysis. No cron job called coach_analyze_and_advise(),
--    so advice could only ever appear if someone called it by hand.
-- 3. Any outcome string was accepted. coach_log_run(..., 'success') went in
--    without complaint and counted as a failure, because only 'succeeded'
--    counts. Same for phase: any text, where the schema says
--    build/test/debug/fix.
-- 4. coach_recommend() looked up the builder's phase and never used it.
--
-- Fixed: check constraints on both fields (values from models.json
-- success_statuses and the phased-build phases); the analysis deletes
-- advice that no longer has more than 5 runs in the window; coach_recommend
-- serves only advice refreshed in the last 30 days, so a stopped schedule
-- degrades to "no advice" rather than old advice; a nightly job runs the
-- analysis ten minutes before hub-nightly; the dead lookup is gone.
-- Self-test: 6 checks.

alter table coach_runs add constraint coach_runs_success_status_chk
  check (success_status in ('succeeded', 'needed_iteration', 'failed', 'partial'));
alter table coach_builder_profile add constraint coach_builder_profile_phase_chk
  check (phase is null or phase in ('build', 'test', 'debug', 'fix'));

-- signature unchanged since 0021 (OUT column queried_task_type, the rename
-- that fixed the original ambiguity crash); only the body changes
create or replace function coach_analyze_and_advise(p_task_type text default null)
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
    where cr.task_type = v_task and cr.model_id = v_model
      and cr.created_at > now() - interval '30 days';

    if v_runs > 5 then
      select cr.effort into v_best_effort
      from coach_runs cr
      where cr.task_type = v_task and cr.model_id = v_model
        and cr.created_at > now() - interval '30 days'
      group by cr.effort
      order by
        sum(case when cr.success_status = 'succeeded' then 1 else 0 end)::numeric / count(*) desc,
        count(*) desc
      limit 1;

      insert into coach_advice (
        task_type, model_id, recommended_effort, confidence, rationale, based_on_runs
      ) values (
        v_task, v_model, v_best_effort, v_success_rate,
        format('%s runs, %s%% success rate, $%s avg cost (last 30 days)', v_runs, round(v_success_rate * 100), round(v_avg_cost, 4)),
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

  -- advice whose pair no longer has more than 5 runs in the window goes
  delete from coach_advice ca
  where (p_task_type is null or ca.task_type = p_task_type)
    and (select count(*) from coach_runs cr
         where cr.task_type = ca.task_type and cr.model_id = ca.model_id
           and cr.created_at > now() - interval '30 days') <= 5;

  return query
  select
    coalesce(p_task_type, 'all'),
    (select count(*) from coach_advice ca where (p_task_type is null or ca.task_type = p_task_type))::integer,
    (select count(*) from coach_lessons cl where (p_task_type is null or cl.task_type = p_task_type))::integer;
end $$;

revoke execute on function coach_analyze_and_advise(text) from public, anon, authenticated;

create or replace function coach_recommend(p_task_type text, p_builder_id text default null)
returns table (
  model_id text,
  model_name text,
  effort text,
  confidence numeric,
  rationale text,
  alternative_model text,
  alternative_effort text
) language plpgsql stable set search_path = public as $$
begin
  return query
  with ranked as (
    select
      a.model_id, m.name, a.recommended_effort, a.confidence, a.rationale,
      row_number() over (order by a.confidence desc) as rn
    from coach_advice a
    join coach_models m on a.model_id = m.model_id
    where a.task_type = p_task_type
      and a.confidence >= 0.70
      and a.last_updated_at > now() - interval '30 days'
  )
  select
    top.model_id, top.name, top.recommended_effort, top.confidence, top.rationale,
    alt.model_id, alt.recommended_effort
  from ranked top
  left join ranked alt on alt.rn = 2
  where top.rn = 1;
end $$;

revoke execute on function coach_recommend(text, text) from public, anon, authenticated;

-- Runs only inside hub_selftest(), whose raise rolls every write back.
-- Called directly it leaves coach-run rows in the append-only log; wrap a
-- direct call in begin; ... rollback;
create or replace function _hub_selftest_coach() returns integer
language plpgsql volatile set search_path = public as $$
declare v_run_id bigint; v_advice record; v_runs integer; v_raised boolean := false;
begin
  -- C1 a run is logged and its id comes back
  select coach_log_run('chat', 'claude-haiku-4-5-20251001', 'high', '_qc_coach_selftest', 'succeeded',
                       5000, 2000, 0.015, 30, 'selftest', null, '_qc_builder', 'build') into v_run_id;
  if v_run_id is null then raise exception 'FAIL C1 coach_log_run returned null'; end if;

  -- C2 no advice before enough runs
  select * into v_advice from coach_recommend('_qc_coach_selftest');
  if v_advice is not null then raise exception 'FAIL C2 expected no advice before runs'; end if;

  -- C3 more than 5 runs produce advice
  for v_runs in 1 .. 6 loop
    perform coach_log_run('chat', 'claude-sonnet-5', 'medium', '_qc_coach_selftest', 'succeeded',
                          8000, 3000, 0.045, 45, 'selftest ' || v_runs, null, '_qc_builder', 'build');
  end loop;
  perform coach_analyze_and_advise('_qc_coach_selftest');
  select * into v_advice from coach_recommend('_qc_coach_selftest');
  if v_advice is null then raise exception 'FAIL C3 analysis did not generate advice after 5+ runs'; end if;

  -- C4 favorite_model is the most-used model, not the last one logged
  if (select favorite_model from coach_builder_profile where builder_id = '_qc_builder') <> 'claude-sonnet-5' then
    raise exception 'FAIL C4 favorite_model was not computed from run frequency';
  end if;

  -- C5 advice expires once its runs leave the 30-day window
  update coach_runs set created_at = now() - interval '90 days' where task_type = '_qc_coach_selftest';
  perform coach_analyze_and_advise('_qc_coach_selftest');
  if exists (select 1 from coach_advice where task_type = '_qc_coach_selftest') then
    raise exception 'FAIL C5 stale advice survived the analysis';
  end if;

  -- C6 a misspelled outcome is refused, not counted as a failure
  begin
    perform coach_log_run('chat', 'claude-sonnet-5', 'medium', '_qc_coach_selftest', 'success');
  exception when check_violation then v_raised := true;
  end;
  if not v_raised then raise exception 'FAIL C6 outcome ''success'' was accepted'; end if;

  delete from coach_advice where task_type = '_qc_coach_selftest';
  delete from coach_runs where task_type = '_qc_coach_selftest';
  delete from coach_builder_profile where builder_id = '_qc_builder';
  return 6;
end $$;

revoke execute on function _hub_selftest_coach() from public, anon, authenticated;

-- the analysis nightly, ten minutes before hub-nightly (0 8 * * * UTC);
-- hub_security_audit() flags any job missing from settings.cron_allowlist
-- as high, so the job is declared there in the same change
do $$
begin
  if exists (select 1 from pg_extension where extname = 'pg_cron') then
    perform cron.schedule('coach-nightly', '50 7 * * *', 'select coach_analyze_and_advise()');
    update settings set value = value || ',coach-nightly', updated_at = now()
    where key = 'cron_allowlist'
      and not ('coach-nightly' = any (string_to_array(replace(value, ' ', ''), ',')));
  end if;
end $$;

select hub_migrated('0024_coach_fix4');
