# Advanced Techniques

This is the material that separates a skill written once and never revisited from one that's been through the loop teams actually use internally when a skill has to work reliably across a huge range of real phrasings and inputs. None of it is exotic — it's just not visible from reading a single SKILL.md file, because it lives in the *process* of building one, not the artifact itself.

## Table of contents

1. Token economy and why scripts can be free
2. Script-first design, worked example
3. Eval-driven iteration (trigger evals + output evals)
4. Reading transcripts, not just outputs
5. Blind grading and why order bias is real
6. Train/test splitting a description-tuning loop
7. Explain the why, skip the ALL-CAPS
8. The overfitting trap
9. Namespacing and silent trigger collisions
10. Skill vs. CLAUDE.md vs. slash command
11. Packaging and background execution

## 1. Token economy and why scripts can be free

The three progressive-disclosure layers (metadata / body / bundled resources) aren't just an organizational nicety — they're a cost model. Metadata is paid on every single conversation regardless of use. The body is paid once triggering happens. Bundled `references/` files are paid only if the body's instructions actually point Claude to read them.

`scripts/` are different in kind, not just degree: a script Claude *executes* consumes essentially none of the model's context budget for its internal logic — only its inputs and outputs pass through context, not the algorithm itself. A 200-line deterministic PDF-field-mapping routine written as prose in SKILL.md costs 200 lines of context on every trigger and gets re-derived (imperfectly, with drift) by the model each time. The same routine as `scripts/fill_form.py`, invoked with one line ("run `python3 scripts/fill_form.py <input> <output>`"), costs a few lines and runs identically every time. This is the single biggest lever for keeping a skill both cheap and reliable, and it's the reasoning behind Step 3 in SKILL.md.

## 2. Script-first design, worked example

**Bad (prose-only):** a SKILL.md for "normalize this CSV export" that describes, in English, an 18-step column-detection and reformatting algorithm. Every run, Claude re-implements the algorithm from the description. Minor variations creep in — a date format handled slightly differently, a column-matching heuristic applied a bit looser or stricter — because natural-language instructions don't pin down every edge case the way code does.

**Good:** the same skill ships `scripts/normalize_csv.py`, a real, tested script that does the deterministic 18 steps. SKILL.md's body becomes: "Run `scripts/normalize_csv.py <input.csv>`. If it reports unmapped columns, use judgment to map them based on [criteria], then re-run with `--column-map`." Now the deterministic 90% is bulletproof and identical every time, and the 10% requiring judgment is exactly what's left in prose — which is exactly what a language model is good at.

The tell that you need this pattern: if you catch yourself writing a numbered list of more than ~5 steps where every step has one obviously correct way to do it, that list should probably become a script instead of an instruction.

## 3. Eval-driven iteration

There are two different things worth evaluating, and they're evaluated differently:

- **Does it trigger correctly?** — tested with a set of should-fire and shouldn't-fire prompts (see `description-formulas.md` and the "Train/test splitting" section below).
- **Does it produce a good result once triggered?** — tested with realistic task prompts and either objective assertions (for deterministic outputs: "the output CSV has a `margin_pct` column", "the PDF has exactly 3 form fields filled") or human judgment (for anything requiring taste).

The rigorous version of the second kind runs the *same prompt* two ways in parallel — once with the skill available, once without (or, when revising an existing skill, once with the old version and once with the new) — using independent subagents so neither run can see or be influenced by the other. The point isn't just "does it work," it's "is the skill actually responsible for the improvement," which a single run in isolation can never tell you. If your environment doesn't support spawning independent agents, this degrades gracefully to running it yourself and leaning harder on a human reviewing the result — a real but weaker signal, and worth saying so out loud rather than presenting it with false confidence.

## 4. Reading transcripts, not just outputs

The final output tells you if the run succeeded. The transcript tells you *why*, and it's where the highest-value signal for the next revision usually hides. Two patterns to watch for specifically:

- **Convergent improvisation** — independent runs on different test prompts all end up writing a similar one-off helper, or all take the same multi-step detour to reach the same intermediate state. That's the script-first signal from §2, discovered empirically instead of guessed at up front: write it once, ship it in `scripts/`, and every future run skips the detour.
- **Wasted motion** — a run spends a large share of its steps on something that never shows up in or affects the final output (re-reading files it already has, re-deriving a fact stated in the skill, second-guessing an instruction that was actually unambiguous). This usually means the body is unclear or contradicts itself somewhere upstream of that point — worth tightening even though the final output "looked fine."

## 5. Blind grading and why order bias is real

When comparing two versions of an output (old skill vs. new, or with-skill vs. baseline), have the judgment made by an agent that doesn't know which output is which, and randomize which one it sees first. This isn't paranoia — graders (human or model) measurably favor whichever answer they evaluate first or whichever they're told is "the new one," independent of actual quality. Blinding the comparison is the cheap fix, and it matters more the closer the two outputs are in quality, which is exactly the regime you're in during late-stage iteration when it's hardest to tell by eye.

## 6. Train/test splitting a description-tuning loop

If you've built a real eval set for triggering (see `description-formulas.md`), the mature version of tuning it mirrors a standard machine-learning safeguard: split the eval prompts roughly 60/40, only look at the 60% ("train") while iterating on the description, and check the held-out 40% ("test") only at the end. A description that scores perfectly on the exact prompts you iterated against but drops on the held-out set has been overfit to your specific phrasings rather than to the underlying intent — exactly analogous to a model memorizing training data instead of generalizing. Re-run each prompt multiple times when trigger behavior seems inconsistent — LLM-judged triggering isn't perfectly deterministic, and a single run of a borderline case is noisy.

## 7. Explain the why, skip the ALL-CAPS

A wall of `ALWAYS do X`, `NEVER do Y` reads as authoritative but tends to produce brittle, overly literal compliance: the model follows the letter of the rule even in the case you didn't anticipate when you wrote it, because it has no reasoning to extrapolate from — just a command. A sentence of causal explanation ("do X before Y, because Y silently corrupts state if run first") gives the model something to reason *with* on the edge case you didn't foresee, and current models are good enough at that reasoning for it to reliably beat the rigid version in practice. Reserve genuinely hard, no-exceptions constraints (safety-relevant, correctness-relevant) for actual imperatives — but even those land better paired with the reason than bare.

## 8. The overfitting trap

It's tempting, once you and the user have three test cases you both understand deeply, to keep patching the skill until it handles those three perfectly — adding a special case for each wrinkle you find. This produces a skill that's excellent at exactly three things and often actively worse at the thousandth unseen real request, because the special-casing crowded out the general instruction that would have covered it. When a problem is stubborn across multiple test cases, the higher-leverage move is usually to find a different general framing or metaphor for the instruction, not to add another exception clause. Test the fix conceptually against a case you *haven't* tried yet before deciding it's solved.

## 9. Namespacing and silent trigger collisions

Skills can be scoped several ways, and the scoping affects who sees them and how conflicts resolve:

- A **plugin-provided** skill is invoked as `plugin-name:skill-name` when disambiguation is needed.
- A **directory-scoped** skill is listed with a path prefix (e.g. `apps/web:deploy`); when a scoped and an unscoped skill share a name, the one whose directory contains the current work wins — most specific match, not registration order.
- Ordinary **project** (`.claude/skills/`) and **personal** (`~/.claude/skills/`) skills have no such prefix and simply compete on description quality alone.

The failure mode worth knowing about: two skills can silently compete for the same trigger with no error surfaced anywhere — an overly broad description on skill A quietly absorbs a request that should have gone to skill B, and the only symptom is "the wrong skill ran" or "the right skill never seems to fire," which looks identical to a plain under-triggering bug. If you maintain more than one or two skills, periodically read all their descriptions side by side, not just the one you're currently editing.

## 10. Skill vs. CLAUDE.md vs. slash command

Three different mechanisms that all shape Claude's behavior, suited to different jobs:

- **CLAUDE.md** — always loaded, every conversation in that project. Right for standing context that's *always* relevant: this repo's conventions, how to run its tests, house style. Wrong for anything conditional, because it's paid on every turn whether or not it's relevant.
- **Skill** — conditionally loaded based on a triggering judgment call. Right for a specialized, repeatable capability that's only relevant *sometimes*: filling a specific document format, running a multi-step build pipeline, applying a review checklist. This is what lets you bundle a lot of depth (references, scripts) without taxing every unrelated conversation.
- **Slash command** — explicitly invoked by the user typing `/name`. Right for something the user wants to trigger on demand and deliberately, with no ambiguity about intent — no description-quality risk, because there's no triggering judgment call to get right or wrong.

If you're building something and unsure which of these three it should be, ask: is this always relevant here (CLAUDE.md), sometimes relevant and Claude should recognize when (skill), or something the user will always ask for by name (slash command)?

## 11. Packaging and background execution

A finished skill folder can be packaged into a single distributable file for sharing or installing elsewhere, rather than copying a directory tree by hand — if the heavier `skill-creator` skill is available in your environment, it ships a `scripts/package_skill.py` that does this. Separately: a skill can be built to run inside a forked subagent rather than the main conversation, returning only its finished result back — worth knowing about for a skill that does heavy, self-contained research or generation work, since it keeps that work's intermediate noise out of the parent conversation's context entirely rather than just deferring it.
