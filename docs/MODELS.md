# Claude Model Coaching & Selection

A guide to every Claude model, how to use it, effort levels, pricing per plan, and when each excels.

## The model lineup

| Model | Capability | Best for | Context | Max Output | Cost | Notes |
|---|---|---|---|---|---|---|
| **Fable 5.1** | Most capable | Complex reasoning, coding, research, long agentic runs, thinking-intensive tasks | 200K | 128K | 50% weekly limits on Max plans; credits required | Fast, optimized for difficult problems; **default for debug & complex phases** |
| **Opus 5.5** | Very capable + speed | Long agentic workflows, structured reasoning, multi-step tasks | 1M | 128K | Premium (Max/Team/Enterprise); native to fast mode | Balanced reasoning + output speed; **default for build & test phases** |
| **Opus 5** | Very capable | Complex workflows, long agentic tasks | 1M | 128K | Max/Team/Enterprise only | Slightly slower than 5.5; same reasoning quality |
| **Sonnet 5** | Capable | Most work: coding, analysis, writing, extraction, few-shot learning | 1M | 128K | All plans (free mentions) | Sweet spot for general purpose; good effort scaling |
| **Haiku 4.5** | Capable + fast | Quick classification, summarization, drafting, training mode, rapid iteration | 200K | 128K | All plans (free mentions) | Cheapest; excellent for feedback loops and learning |

## Availability by plan

### Free
- Haiku 4.5
- Sonnet 5
- Limited usage; no Claude Code, API, or advanced features

### Pro ($17–20/month)
- Haiku 4.5 (primary)
- Sonnet 5 (access)
- Opus 5.5 (limited, via model picker or 3x multiplier if you switch)
- Claude Code (included)
- 1M requests/month cap

### Max ($100/month, 5x usage)
- All models: Haiku, Sonnet, Opus 5.5, Opus 5, Fable 5.1 (50% of Fable's weekly limits; needs credits for overages)
- Claude Code (included)
- Fast mode (2.5x output speed, premium pricing, Opus 5.5/5/4.8 only)
- 5M requests/month effective cap (with usage multiplier)
- Higher rate limits per second

### Max 20x ($200/month, 20x usage)
- Same as Max ($100) but with 20x multiplier
- 20M requests/month effective cap

### Team ($20–100/seat/month)
- All models (depends on tier)
- Workspace sharing, org-level settings
- Custom rate limits

### Enterprise
- All models, unlimited
- Custom everything

## Effort levels

Effort controls how hard the model thinks. Every model supports effort assignment (via `/effort`, settings, or API `budget_tokens` equivalent).

| Effort | What it does | Good for | Cost |
|---|---|---|---|
| **low** | Fast, surface-level answers | Drafts, brainstorming, feedback loops, training runs | 1x |
| **medium** | Default for Opus 5.5; standard reasoning | Most work: coding, analysis, writing | 1.5–2x |
| **high** | Deliberate reasoning; default for Sonnet/Haiku | Problems that need thought; detailed answers | 2–3x |
| **xhigh** | Extended thinking (Fable/Opus only); deep reasoning | Hard problems, novel approaches, edge cases | 4–6x |
| **max** | Full thinking budget; very slow, most thorough | Research-grade reasoning only; debugging | 8–10x |

**Key insight:** Haiku at high/xhigh effort can match Sonnet's results on many tasks. Sonnet at high effort often matches Opus. *Training* the system to recognize what effort each task truly needs saves money and trains lower-cost models faster.

## Use-case matrix: which model when

### Drafting & ideation
- **Haiku (low)** — fastest feedback loop; train the system on what you actually want
- Sonnet (low) — if Haiku is too constrained
- *Goal:* iterate fast, don't think hard yet

### Coding & debugging
- **Fable 5.1** — use only for debug phase (when something's broken and you need it fixed)
- **Opus 5.5 (medium–high)** — implement features, architect design, multi-file changes
- Sonnet (high) — good for most changes if budget is tight
- Haiku (xhigh) — acceptable if you're training the system to recognize patterns

### Writing, analysis, research
- **Opus 5.5 (medium)** — long-form, nuanced reasoning
- Sonnet (medium–high) — good default; train it on your style
- Haiku (high) — if iteration speed matters more than perfection
- *Goal:* capture patterns so lower-cost models can replicate

### Agentic work (long multi-step loops)
- **Opus 5.5** — orchestrate long runs unattended; handles context window gracefully
- Opus 5 — same capability, slightly slower
- Sonnet (high) — works if you're monitoring and steering

### Classification, extraction, QC
- **Haiku (high–xhigh)** — these tasks are simple enough; train it here
- Sonnet (medium) — overkill; use Haiku first
- *Why:* scaling Haiku's performance on these benchmarks means cheaper downstream work

## Pricing breakdown

**Monthly cost estimates** (based on Max plan, assumed usage patterns):

| Scenario | Haiku | Sonnet | Opus 5.5 | Fable 5.1 | Notes |
|---|---|---|---|---|---|
| Light use (10 requests/day, avg 5K input + 2K output) | <$0.50 | $2–5 | $10–15 | — | Haiku dominates |
| Moderate (50 requests/day, avg 10K input + 3K output) | $2–3 | $10–20 | $40–60 | $20–30 (credits) | Sonnet is sweet spot |
| Heavy (500 requests/day, large batches) | $20–30 | $100–150 | $400–600 | $200–300 (credits) | Opus 5.5 if speed matters; else mix models |
| Debug/iteration (10 debug runs, Fable + re-runs) | — | — | $50–100 | $100–200 | Fable for hard parts only |

*All figures assume Max plan (5x multiplier). Pro plan costs are ~5x higher per request.*

## The phased-build workflow

Dexter's build system uses four sequential phases; each phase picks different models based on need:

### Phase 1: Build (untested code, speed prioritized)
- **Primary:** Opus 5.5 (medium effort, stream output)
- **Fallback:** Sonnet (high effort) if speed or budget is tight
- **Not:** Haiku (not good enough yet; xhigh effort too slow)
- **Why:** You need fast, capable output; testing comes later

### Phase 2: Test (run the suite)
- **Primary:** Haiku (run fast feedback loops, catch obvious breaks)
- **Secondary:** Sonnet (if Haiku misses edge cases)
- **Not:** Fable/Opus yet; no complex reasoning needed
- **Why:** iterate test failures quickly; keep running costs low

### Phase 3: Debug (root-cause real failures)
- **Primary:** Fable 5.1 (xhigh effort, thinking; this is where it earns its cost)
- **Secondary:** Opus 5.5 (medium effort, if Fable doesn't land)
- **Fallback:** Sonnet (high effort) for narrow, known failures
- **Why:** Real problems need hard thinking; this is the phase where Fable pays for itself

### Phase 4: Fix & ship (implement, validate, merge)
- **Primary:** Opus 5.5 (medium effort; you know what's broken now)
- **Secondary:** Sonnet (high effort) for straightforward fixes
- **Test with:** Haiku (train it on the actual fix)
- **Why:** implement fast; verify with the cheap model; ship

## Effort tuning by task type

Start here if you're not sure what effort to pick:

| Task | Start | Scale up if | Scale down if |
|---|---|---|---|
| Generate code | Opus (medium) | It's complex/novel | It's routine/templated |
| Debug code | Fable (xhigh) | Didn't work | It's a typo/config |
| Write docs/copy | Sonnet (medium) | It needs voice/nuance | It's boilerplate |
| Extract data | Haiku (high) | It keeps missing fields | Pattern is obvious |
| Long agentic run | Opus 5.5 (medium, stream) | Hitting token limits | Single step works fine |
| Brainstorm ideas | Haiku (low) | Haiku's stuck | Ideas are good, ship them |

## The coaching system: learning from every run

The hub logs every model invocation, effort level, task type, and outcome. Over time:

1. **Patterns emerge:** "Haiku at high effort solves 70% of Sonnet's medium-effort work on this task type"
2. **Boundaries are pushed:** Lower models learn to handle harder problems through training
3. **Recommendations improve:** "For your coding style, Haiku at xhigh usually lands it in one shot"
4. **Cost scales with capability:** You keep getting results while spending less

The coaching engine (migration 0020) tracks:
- Which model + effort you used
- What task type it was
- Whether it succeeded / needed iteration
- What the actual token cost was
- Lessons learned (notes for next time)

This trains both you and the models you work with.

## Model switching (Claude Code)

If you need to change models mid-session:

```bash
/model fable        # Switch to Fable 5.1
/model opus         # Opus 5.5 or 5 (resolved per plan)
/model sonnet       # Sonnet 5
/model haiku        # Haiku 4.5
/model default      # Back to session default (from settings)

/effort low         # For the next request
/effort high        # Deep reasoning
/effort xhigh       # Extended thinking (if supported)
```

Or set in `settings.json`:
```json
{
  "model": "sonnet",
  "effort": "high"
}
```

## API model IDs

When building against the Claude API:

```
claude-fable-5-1              # Fable 5.1
claude-opus-5-5               # Opus 5.5
claude-opus-5                 # Opus 5
claude-sonnet-5               # Sonnet 5
claude-haiku-4-5-20251001     # Haiku 4.5
```

Use aliases in client code when possible (`client.models.default`, etc.), not hardcoded IDs.

## Fast mode

Available on Max plans for Opus 5.5, Opus 5, and Opus 4.8. Produces output 2.5x faster but costs 1.5–2x per token. Not recommended for interactive use; excellent for batch/agentic work that must complete on schedule.

```bash
/fast               # Toggle on
/slow               # Toggle off (normal speed, normal cost)
```

## Thinking (adaptive, all models)

Newer models (Fable 5.1, Opus 5.5/5, Sonnet 5, Haiku 4.5) use adaptive thinking: the model decides whether it needs to think hard on this particular request. You don't control it directly; effort level affects how much thinking budget is available.

On xhigh effort, expect thinking blocks for complex problems.

---

Last updated: 2026-09-27 · See also: `models.json` (machine-readable catalog), hub migration 0020 (coaching schema)
