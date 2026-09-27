-- 0020_coach: model coaching, run logging, and builder profile learning
--
-- Tracks every model invocation, effort level, task type, and outcome
-- so the hub can learn patterns and recommend better model/effort pairs.
-- Teaches lower-cost models to handle harder tasks. Records the builder's
-- evolving patterns for proactive coaching.

-- Catalog of Claude models and their metadata
create table if not exists coach_models (
  model_id text primary key,
  name text not null,
  capability_tier text not null, -- most_capable, very_capable, capable, capable_fast
  context_window integer not null,
  max_output_tokens integer not null,
  thinking_support text not null default 'adaptive', -- adaptive, none
  default_effort text not null, -- low, medium, high, xhigh, max
  use_cases text[] default '{}',
  strengths text[] default '{}',
  weaknesses text[] default '{}',
  cost_per_mtok_input numeric(6,2),
  cost_per_mtok_output numeric(6,2),
  supports_fast_mode boolean default false,
  phase_recommendation text, -- build_only, test_only, debug_only, build_test_fix, etc.
  created_at timestamp default now()
);

-- Effort level definitions and mechanics
create table if not exists coach_effort (
  effort text primary key,
  description text not null,
  use_for text[] default '{}',
  thinking_enabled boolean,
  cost_multiplier numeric(4,1),
  created_at timestamp default now()
);

-- Coaching recommendations: "for this task_type + model combo, try this effort"
create table if not exists coach_advice (
  id bigserial primary key,
  task_type text not null,
  model_id text not null references coach_models(model_id),
  recommended_effort text not null,
  confidence numeric(3,2), -- 0.0–1.0, based on run data
  rationale text,
  based_on_runs integer default 0, -- how many runs this advice came from
  last_updated_at timestamp default now(),
  foreign key (recommended_effort) references coach_effort(effort)
);

-- Run log: every model invocation, effort, task, and outcome
create table if not exists coach_runs (
  id bigserial primary key,
  surface text not null, -- 'code', 'chat', 'cowork', etc.
  session_id text,
  chat_id text,
  model_id text not null references coach_models(model_id),
  effort text not null references coach_effort(effort),
  task_type text not null,
  task_description text,
  success_status text not null, -- succeeded, needed_iteration, failed, partial
  retry_count integer default 0,
  input_tokens integer,
  output_tokens integer,
  thinking_tokens integer default 0,
  cost_usd numeric(6,4),
  duration_seconds integer,
  notes text,
  builder_lesson text, -- if something unexpected happened, note it
  created_at timestamp default now()
);

create index coach_runs_model_effort on coach_runs(model_id, effort);
create index coach_runs_task_type on coach_runs(task_type);
create index coach_runs_success on coach_runs(success_status);
create index coach_runs_created on coach_runs(created_at desc);

-- Lessons learned: coaching notes per task_type + model_combo
create table if not exists coach_lessons (
  id bigserial primary key,
  task_type text not null,
  model_id text not null references coach_models(model_id),
  lesson text not null,
  confidence text, -- proven, tested, expected
  observations integer, -- how many runs informed this
  impact_on_cost numeric(4,2), -- e.g. 0.60 = 40% cheaper
  impact_on_quality text, -- same, better, worse, tradeoff
  created_at timestamp default now(),
  updated_at timestamp default now()
);

-- Builder profile: learned patterns in how Dex works
create table if not exists coach_builder_profile (
  builder_id text primary key,
  phase text, -- build, test, debug, fix; what they're most often doing
  favorite_model text references coach_models(model_id),
  reliable_effort text references coach_effort(effort),
  prefers_speed boolean default false,
  prefers_accuracy boolean default false,
  trains_models boolean default true,
  common_task_types text[], -- which tasks come up most
  known_constraints text[], -- "200K context too small", "needs output in 30s", etc.
  last_phase_run text,
  last_model_switch timestamp,
  total_runs integer default 0,
  total_cost_usd numeric(10,2) default 0,
  cost_per_week_usd numeric(8,2) default 0,
  updated_at timestamp default now()
);

-- Coaching recommendations API
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
declare v_builder_phase text;
begin
  -- if builder profile exists, factor in their phase
  if p_builder_id is not null then
    select phase into v_builder_phase from coach_builder_profile where builder_id = p_builder_id;
  end if;

  return query
  select
    a.model_id,
    m.name,
    a.recommended_effort,
    a.confidence,
    a.rationale,
    null::text,
    null::text
  from coach_advice a
  join coach_models m on a.model_id = m.model_id
  where a.task_type = p_task_type
    and a.confidence >= 0.70
  order by a.confidence desc
  limit 1;
end $$;

-- Log a run and update builder profile
create or replace function coach_log_run(
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
  p_builder_id text default null
)
returns bigint language plpgsql volatile set search_path = public as $$
declare v_run_id bigint;
begin
  insert into coach_runs (
    surface, session_id, model_id, effort, task_type,
    success_status, input_tokens, output_tokens,
    cost_usd, duration_seconds, notes
  ) values (
    p_surface, p_session_id, p_model_id, p_effort, p_task_type,
    p_success_status, p_input_tokens, p_output_tokens,
    p_cost_usd, p_duration_seconds, p_notes
  )
  returning id into v_run_id;

  -- update builder profile if given
  if p_builder_id is not null then
    insert into coach_builder_profile (
      builder_id, phase, favorite_model, total_runs, total_cost_usd, updated_at
    ) values (
      p_builder_id, p_task_type, p_model_id, 1, coalesce(p_cost_usd, 0), now()
    )
    on conflict (builder_id) do update set
      favorite_model = coalesce(excluded.favorite_model, coach_builder_profile.favorite_model),
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

-- Analyze runs to generate or update coaching advice
create or replace function coach_analyze_and_advise(p_task_type text default null)
returns table (
  task_type text,
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
begin
  for v_task, v_model in
    select distinct task_type, model_id from coach_runs
    where (p_task_type is null or task_type = p_task_type)
      and created_at > now() - interval '30 days'
  loop
    select
      count(*),
      sum(case when success_status = 'succeeded' then 1 else 0 end)::numeric / count(*),
      avg(cost_usd)::numeric,
      avg(output_tokens)::integer
    into v_runs, v_success_rate, v_avg_cost, v_avg_tokens_out
    from coach_runs
    where task_type = v_task and model_id = v_model;

    -- update or create advice based on success rate and cost
    if v_runs > 5 then
      insert into coach_advice (
        task_type, model_id, recommended_effort, confidence, rationale, based_on_runs
      ) select
        v_task, v_model, effort, v_success_rate,
        format('%.0f runs, %s success rate, $%.4f avg cost', v_runs, round(v_success_rate * 100), v_avg_cost),
        v_runs
      from coach_effort
      where effort in (select distinct effort from coach_runs
                       where task_type = v_task and model_id = v_model
                       order by success_status = 'succeeded' desc limit 1)
      on conflict (task_type, model_id) do update set
        confidence = excluded.confidence,
        based_on_runs = excluded.based_on_runs,
        last_updated_at = now();
    end if;
  end loop;

  return query
  select
    coalesce(p_task_type, 'all'),
    (select count(*) from coach_advice where (p_task_type is null or task_type = p_task_type))::integer,
    (select count(*) from coach_lessons where (p_task_type is null or task_type = p_task_type))::integer;
end $$;

-- ---------------------------------------------------------------------------
-- Bootstrap: populate coach_models and coach_effort from known catalog
-- ---------------------------------------------------------------------------

insert into coach_models (model_id, name, capability_tier, context_window, max_output_tokens, default_effort, cost_per_mtok_input, cost_per_mtok_output, supports_fast_mode, phase_recommendation) values
  ('claude-fable-5-1', 'Fable 5.1', 'most_capable', 200000, 128000, 'high', 3.0, 15.0, false, 'debug_only'),
  ('claude-opus-5-5', 'Opus 5.5', 'very_capable', 1000000, 128000, 'medium', 3.0, 15.0, true, 'build_test_fix'),
  ('claude-opus-5', 'Opus 5', 'very_capable', 1000000, 128000, 'high', 3.0, 15.0, true, 'build_debug'),
  ('claude-sonnet-5', 'Sonnet 5', 'capable', 1000000, 128000, 'high', 3.0, 15.0, false, 'build_test_fix'),
  ('claude-haiku-4-5-20251001', 'Haiku 4.5', 'capable_fast', 200000, 128000, 'high', 0.8, 4.0, false, 'test_training')
on conflict (model_id) do nothing;

insert into coach_effort (effort, description, thinking_enabled, cost_multiplier) values
  ('low', 'Fast, surface-level answers', false, 1.0),
  ('medium', 'Standard reasoning', true, 1.5),
  ('high', 'Deliberate reasoning', true, 2.5),
  ('xhigh', 'Extended thinking, deep reasoning', true, 5.0),
  ('max', 'Full thinking budget, very thorough', true, 8.0)
on conflict (effort) do nothing;

-- ---------------------------------------------------------------------------
-- Self-test (inside the self-test's rollback)
-- ---------------------------------------------------------------------------
create or replace function _hub_selftest_coach() returns integer
language plpgsql volatile set search_path = public as $$
declare v_run_id bigint; v_advice record; v_runs integer;
begin
  -- C1 log a run and get the id back
  select coach_log_run('chat', 'claude-haiku-4-5-20251001', 'high', 'coding', 'succeeded',
                       5000, 2000, 0.015, 30, 'Haiku handled quick fix') into v_run_id;
  if v_run_id is null then raise exception 'FAIL C1 coach_log_run returned null'; end if;

  -- C2 recommended model for a task type (advice not yet seeded)
  select * into v_advice from coach_recommend('coding');
  if v_advice is not null then raise exception 'FAIL C2 expected no advice before runs'; end if;

  -- C3 analyze runs and generate advice (need more than 5 runs for advising)
  for v_runs in 1 .. 6 loop
    perform coach_log_run('chat', 'claude-sonnet-5', 'medium', 'coding', 'succeeded',
                          8000, 3000, 0.045, 45, 'Sonnet coding run ' || v_runs);
  end loop;

  perform coach_analyze_and_advise('coding');

  select * into v_advice from coach_recommend('coding');
  if v_advice is null then raise exception 'FAIL C3 analysis did not generate advice after 5+ runs'; end if;

  return 3;
end $$;

revoke execute on all functions in schema public from public, anon, authenticated;
revoke all on all tables in schema public from anon, authenticated;

select hub_migrated('0020_coach');
