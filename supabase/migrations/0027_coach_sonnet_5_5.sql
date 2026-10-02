-- 0027_coach_sonnet_5_5: the catalog learns what shipped from 09-22 to 10-02.
--
-- Read on 2026-10-03 from the four Claude Code newsletters of 09-11 to 10-02,
-- the Opus 5.5 page, the Sonnet 5.5 build blog, "What a task costs on Opus
-- 5.5" and the Claude Code changelog through 2.1.288 (hub raw 1104).
--
--   Sonnet 5.5 (claude-sonnet-5-5) was missing. Added in Claude Code 2.1.284
--     on 09-28 as the default Sonnet: 1M context, 128K output, $2 / $10,
--     over 30% faster than Sonnet 5 with far fewer tokens per task. Default
--     effort is high on the API (the convention every row here follows) and
--     medium in Claude Code.
--   use_cases, strengths and weaknesses were empty on every row. Filled for
--     the three current models from Anthropic's own guidance; the older
--     rows stay empty rather than guessed.
--   Sonnet 5 keeps its row (runs logged against it stay valid) and gives
--     its phase to Sonnet 5.5.

insert into coach_models (model_id, name, capability_tier, context_window, max_output_tokens,
    thinking_support, default_effort, cost_per_mtok_input, cost_per_mtok_output,
    supports_fast_mode, phase_recommendation, use_cases, strengths, weaknesses)
values ('claude-sonnet-5-5', 'Sonnet 5.5', 'capable', 1000000, 128000,
    'adaptive', 'high', 2, 10, false, 'build_test_fix',
    array['well-scoped coding: a bug fix with a clear repro', 'high-volume development',
          'repeatable agent tasks: investigation, review, drafting', 'subagents and lookups'],
    array['over 30% faster than Sonnet 5', 'far fewer tokens per task than Sonnet 5',
          'cache reads $0.20 per million; minimum cacheable prompt 512 tokens'],
    array['not for long-horizon agentic work or judgement-heavy problems (Opus 5.5 or Fable 5.1)',
          'API: thinking "disabled" is now "between_tools"; forced tool_choice is now auto plus strict'])
on conflict (model_id) do nothing;

update coach_models set
    use_cases  = array['features, debugging and code review', 'daily supervised work',
                       'long-horizon agentic coding'],
    strengths  = array['roughly Fable 5.1 level on most work', 'over 30% faster and 40% cheaper than Opus 5',
                       'much less likely to take hard-to-reverse actions; more resistant to prompt injection',
                       'shorter replies; sticks to what was asked'],
    weaknesses = array['thinking cannot be disabled']
  where model_id = 'claude-opus-5-5';

update coach_models set
    use_cases  = array['the longest, hardest runs', 'debugging what Opus 5.5 could not',
                       'high-stakes work where a miss costs more than the tokens'],
    strengths  = array['most capable generally available model',
                       'sustains long autonomous sessions; investigates before acting'],
    weaknesses = array['2.5 times the price of Opus 5.5', 'a run can use up to half the weekly plan limit',
                       'more eager than Fable 5: Anthropic runs it at medium effort where it used high']
  where model_id = 'claude-fable-5-1';

update coach_models set phase_recommendation = 'superseded_by_sonnet_5_5'
  where model_id = 'claude-sonnet-5';

select hub_migrated('0027_coach_sonnet_5_5');
