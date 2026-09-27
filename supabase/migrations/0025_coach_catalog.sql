-- 0025_coach_catalog: correct the model catalog 0020 seeded.
--
-- 0020's rows were written from memory on the first build pass, not from a
-- source. Checked on 2026-09-27 against the Claude API reference bundled
-- with Claude Code (skill claude-api, shared/models.md and
-- shared/model-migration.md). Wrong before this migration:
--   Fable 5.1 context 200K (is 1M); price $3/$15 (is $10/$50)
--   Opus 5.5 price $3/$15 (is $4/$20); Opus 5 price $3/$15 (is $5/$25)
--   Sonnet 5 price $3/$15 (is $2/$10)
--   Haiku 4.5 max output 128K (is 64K); price $0.80/$4 (is $1/$5);
--     thinking 'adaptive' (models before 4.6 use budget_tokens)
-- coach_effort.cost_multiplier (1, 1.5, 2.5, 5, 8) had no source. Effort
-- changes how many tokens a model spends, not the price per token, so a
-- fixed multiplier is not a fact about any model; cleared.

update coach_models set context_window = 1000000, cost_per_mtok_input = 10, cost_per_mtok_output = 50
  where model_id = 'claude-fable-5-1';
update coach_models set cost_per_mtok_input = 4, cost_per_mtok_output = 20
  where model_id = 'claude-opus-5-5';
update coach_models set cost_per_mtok_input = 5, cost_per_mtok_output = 25
  where model_id = 'claude-opus-5';
update coach_models set cost_per_mtok_input = 2, cost_per_mtok_output = 10
  where model_id = 'claude-sonnet-5';
update coach_models set max_output_tokens = 64000, cost_per_mtok_input = 1, cost_per_mtok_output = 5,
    thinking_support = 'budget_tokens'
  where model_id = 'claude-haiku-4-5-20251001';

update coach_effort set cost_multiplier = null;
comment on column coach_effort.cost_multiplier is
  'unused: effort changes tokens spent, not price per token; measure cost from coach_runs.cost_usd';

select hub_migrated('0025_coach_catalog');
