-- 0023_coach_fix3: third QA/QC pass on the model coaching system.
--
-- Found live:
--
-- 1. Migration 0022_coach_fix2 was applied live but its final
--    `select hub_migrated('0022_coach_fix2')` line was never actually
--    executed against the database (dropped when the apply call was
--    split from the file) -- confirmed via the hub's own migration log
--    (`select event, detail->>'name' from log where event='migration'`
--    had no 0022 row despite the code existing in git and being live).
--    This is the exact "code changed with no migration logged" class of
--    drift the hub's own audit exists to catch. Logged now.
--
-- 2. coach_analyze_and_advise() selects candidate (task_type, model_id)
--    pairs using a 30-day window (`created_at > now() - interval '30
--    days'`), but the two queries that then compute the actual stats --
--    the success-rate/cost/token aggregate, and the best-effort pick --
--    have NO time bound at all. They pull every run ever logged for that
--    pair, unbounded. A model/prompt that performed badly months ago and
--    has since improved (or the reverse) never rolls off; "30-day
--    analysis" was true only for which pairs got considered, not for the
--    numbers computed about them. This has been true since 0020 and
--    survived unnoticed through 0021's crash fix and 0022's aggregation
--    fix, because neither touched this part of the function.
--
-- Fixed here: both queries now filter to the same 30-day window as the
-- candidate-selection loop, so "confidence" and "recommended effort"
-- actually reflect recent performance, not all-time history.

-- NOTE: the live/0021 signature returns `queried_task_type`, not
-- `task_type` -- that rename is what fixed the original ambiguity bug.
-- This migration only changes the function body (adds the 30-day bound
-- to two internal queries), so CREATE OR REPLACE is used, matching the
-- existing OUT-parameter name exactly. Do not revert it to `task_type`.

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

  return query
  select
    coalesce(p_task_type, 'all'),
    (select count(*) from coach_advice ca where (p_task_type is null or ca.task_type = p_task_type))::integer,
    (select count(*) from coach_lessons cl where (p_task_type is null or cl.task_type = p_task_type))::integer;
end $$;

revoke execute on function coach_analyze_and_advise(text) from public, anon, authenticated;

select hub_migrated('0023_coach_fix3');
