---
name: skill-builder
description: Interactively designs, drafts, validates, tests, and tunes high-quality Claude Skills (SKILL.md packages), using the same progressive-disclosure architecture, script-first design, and eval-driven triggering methodology that Anthropic's own skill engineers use internally. Trigger this whenever the user wants to create a new Claude Skill, plugin skill, or slash command; turn a repeated workflow, prompt template, or "Claude always do X this way" habit into something reusable; fix a skill that isn't triggering, is triggering at the wrong time, or is stealing triggers from another skill; or improve, review, package, or debug an existing SKILL.md — even if they don't know the word "skill" and just say things like "can I save this as a shortcut" or "make Claude remember how I like this done."
---

# Skill Builder

You are helping someone build a Claude Skill that will be reused many times across many conversations — possibly thousands. That framing matters: a skill tuned to look good on the one example in front of you, but that breaks or misfires on the 500th slightly-different real request, has failed at its actual job. Everything below optimizes for that.

A Skill is not a prompt. It's three layers Claude loads at different times, and the whole craft of skill-building is deciding what goes in which layer:

1. **Metadata** (`name` + `description`) — always sitting in Claude's context, in every conversation, whether or not the skill is used. This is the *only* signal Claude uses to decide whether to open the skill at all. Cost of being wrong here: the skill never fires, or fires when it shouldn't.
2. **SKILL.md body** — loaded into context only once the skill triggers. This is where you put the workflow, decision points, and pointers — not everything you know about the topic.
3. **Bundled resources** (`scripts/`, `references/`, `assets/`) — loaded (or, for scripts, *executed without ever being loaded*) only when the body points to them. Unlimited size, zero cost until touched.

Most weak skills fail because their author collapsed all three layers into one wall of text. Most strong skills fail to *trigger* because the author wrote the description as a summary instead of a trigger condition. Keep reading — this file walks the build in order, and `references/advanced-techniques.md` holds the deeper, less-commonly-known material this skill is really for.

## Step 1 — Interview before drafting

Don't write SKILL.md from a single sentence. Ask (briefly, conversationally — don't interrogate):

1. **The job**: What should Claude be able to do after this skill exists that it can't reliably do now?
2. **The trigger**: What would the user actually type, in their own words, right before they want this? Get 3-5 realistic phrasings, not one clean example. Include the messy ones ("that thing we do with the client reports").
3. **The shape of the output**: A file? A specific format? A fixed structure the user will paste elsewhere? Get an example of a *good* output if one exists.
4. **Edge cases and variants**: Does this need to branch by framework/platform/format? Is there a wrong way to do this that Claude might default to?
5. **Is it deterministic or judgment-based?** This decides a lot downstream (see Step 3). "Convert this XLSX layout to that one" is deterministic. "Write in our brand voice" is judgment-based.
6. **Worth testing formally?** Deterministic, verifiable outputs (file transforms, fixed report structures, code generation) benefit from real test cases and assertions. Subjective outputs (voice, taste, creative work) mostly need human eyeballs instead — don't force a grading rubric onto something that needs judgment.

If the workflow already happened earlier in this conversation (the user did something manually and now wants it repeatable), mine that history first — the tool sequence, the corrections the user made mid-stream, the input/output pairs — and confirm your read of it before drafting.

## Step 2 — Draft the description first, and make it earn its trigger

The description is doing a completely different job than the body. The body explains *how*; the description's only job is to tell Claude — and only Claude, reading it cold, with none of this conversation's context — *when* to reach for this over everything else it could do. Write it as a trigger condition, not a summary.

The default failure mode is **under-triggering**: Claude reads a bland description ("Helps format reports") and quietly does the task itself without ever opening the skill, because bland descriptions don't distinguish themselves from "just answer the question." Counter this by being concretely, almost aggressively specific about *when*, including the phrasings and contexts a naive description would miss, and by explicitly saying "use this even if the user doesn't say X" for the ways people ask without the obvious keyword.

Full formula, calibration guidance, and before/after rewrites: **`references/description-formulas.md`**. Read it before finalizing the description — this one field determines whether the rest of the skill ever gets used at all.

## Step 3 — Decide what's prose and what's a script

This is the single highest-leverage decision in the whole build, and it's the one most self-taught skill authors never make deliberately. For any step in the workflow, ask: *does this step have one correct algorithm, or does it require judgment?*

- **One correct algorithm** (parsing a file format, renaming a column, computing a hash, filling a template, running a fixed CLI pipeline) → write it as a script in `scripts/` and tell the body to invoke it. A script runs the same way every time, costs no context tokens to execute, and can't hallucinate a step. Prose describing a 12-step deterministic transform will be re-derived slightly differently by Claude nearly every run — sometimes with a bug.
- **Requires judgment** (matching tone, deciding which of several valid structures fits, triaging ambiguous input) → this stays as instructions in the body, because that's exactly the kind of thing a language model is good at and a script is bad at.

Most real skills are a mix. Write the body as: judgment steps in prose, deterministic steps as "run the script that does this." See `references/advanced-techniques.md` for the reasoning and a worked before/after — this is one of the biggest gaps between skills written by people who've iterated on many skills and skills written by people writing their first one.

## Step 4 — Scaffold and write

Use the bundled scaffolder rather than hand-rolling folders:

```bash
python3 .claude/skills/skill-builder/scripts/scaffold_skill.py <skill-name> --path <where-it-should-live>
```

This creates `SKILL.md` with the frontmatter shape filled in and empty `scripts/`, `references/`, `assets/` directories, so you're filling in a known-good structure instead of guessing at conventions.

While writing the body:

- **Keep it under ~500 lines.** If you're pushing past that, you're probably explaining something that belongs in a reference file. Add a pointer instead — e.g. "for the Postgres-specific migration steps, see the postgres reference file."
- **If a reference file will run past ~300 lines, give it a table of contents.** Claude reads reference files by jumping to the relevant section, not linearly — an unsorted 800-line file gets skimmed, not read.
- **Multi-variant skills** (a skill that supports several frameworks, cloud providers, or output formats) should shard by variant, not interleave: one reference file per variant (aws, gcp, azure, say), with the body doing only the "which one applies, and here's the shared workflow" part. Claude then loads exactly one file instead of context it doesn't need.
- **Explain the why, not just the MUST.** Today's models generalize well from a short causal explanation ("do X because Y breaks otherwise") and generalize badly from a wall of ALL-CAPS commands with no reasoning — the second pattern produces brittle, overly literal behavior the moment reality deviates from the exact case you had in mind. If you notice yourself typing NEVER or ALWAYS in caps, pause and ask whether a sentence of reasoning would do the same job more robustly.
- **Don't overfit to the examples in front of you.** A skill tuned to nail the three cases you and the user tested, via increasingly specific special-case rules, is a skill that breaks on case four. If a problem is stubborn, prefer reframing the general instruction over bolting on another exception.

## Step 5 — Validate before you test

Run the bundled linter on the draft:

```bash
python3 .claude/skills/skill-builder/scripts/validate_skill.py <path-to-SKILL.md>
```

It checks the mechanical things that quietly kill skills — malformed or missing frontmatter, a name that doesn't match its directory, a description that reads as a summary instead of a trigger condition, body length, reference files over the table-of-contents threshold without one, and scripts referenced in the body that don't actually exist on disk. Fix everything it flags before moving on; these are exactly the failures that are invisible when you eyeball the file but fatal in practice.

## Step 6 — Test it like it's going to run a thousand times, not once

Write 2-3 realistic test prompts — the kind of thing a real user would actually type, not a clean paraphrase of the spec. For each one:

- If you have access to the `Agent` tool, spawn a fresh subagent pointed at the skill and the prompt, and — when the skill is new — a second one on the *same prompt with no skill at all*. Comparing the two tells you whether the skill is actually earning its keep, not just producing output that looks fine in isolation.
- **Read the transcript, not just the final output.** If independent runs all end up writing their own similar throwaway helper script or all take the same multi-step detour to get somewhere, that's a direct signal that step belongs in `scripts/` as a bundled tool instead of being re-derived every time — go back to Step 3.
- No subagents available (e.g. you're the one both writing and running the skill)? Run the prompts yourself following the skill's own instructions, and say so plainly when you show the user the result — self-graded output is a real but weaker signal than an independent run, so lean harder on the user's own eyes at this stage.

For deterministic/verifiable skills, write assertions per test case (what must be objectively true of the output) rather than relying purely on "looks right." For judgment-based skills, skip assertions and go straight to asking the user what they think.

Iterate: fix based on what actually broke, re-run, repeat until the user is satisfied or you've stopped making real progress. If the environment has the full `skill-creator` skill available (a more heavyweight sibling of this one, built for exactly this loop), and the stakes justify it — a skill headed for production use across a team — it's worth escalating to it for its parallel-subagent benchmark harness and blind A/B grading; see `references/advanced-techniques.md` for what that buys you and when it's worth the extra time.

## Step 7 — Tune the trigger for real, not just by eye

Eyeballing whether a description "sounds right" catches maybe half the triggering problems. The rest only show up when you actually test it against phrasings you didn't write while thinking about this exact skill. Build a small eval set — 8-10 prompts that *should* trigger it (including ones that never use the skill's own name) and 8-10 that deliberately *shouldn't* (the tricky near-misses that share vocabulary but need something else, not obviously-irrelevant filler). `references/advanced-techniques.md` covers how to build a good negative set and, if `skill-creator`'s automated optimizer is available in this environment, how to run its held-out train/test loop so you're not just overfitting the description to the exact eval prompts you happened to write.

## Step 8 — Ship it in the right place

Where a skill lives changes who can trigger it:

- **Project-scoped** (`.claude/skills/<name>/`, inside a repo like this one): available to anyone working in that repo, versioned alongside the code it's about. Right default for anything tied to this codebase's conventions.
- **Personal** (`~/.claude/skills/<name>/`): available to you across every project. Right default for workflow habits that aren't about any one codebase.
- **Plugin-provided**: bundled and distributed as part of a plugin, invoked as `plugin-name:skill-name` when a name collision needs disambiguating.
- **Directory-scoped**: a skill can be scoped to a subdirectory (shown as `path:skill-name`); when both a scoped and unscoped skill share a name, the one whose directory contains the current work wins — most-specific match, not first-registered.

Before calling it done, do one last check across your *other* skills, not just this one: a description written too broadly can quietly steal triggers meant for a different skill, and you'll never see an error for it — the wrong skill just fires instead. If you maintain more than a couple of skills, skim their descriptions side by side and make sure each one's trigger territory is actually distinct.

## Quick checklist

- [ ] Description states *when*, concretely, not just *what* — read `references/description-formulas.md` self-test
- [ ] Deterministic steps live in `scripts/`, not re-derived in prose every run
- [ ] Body is lean; anything deep or variant-specific is in `references/` with a pointer
- [ ] Reasoning ("because...") backs any hard rule instead of a bare MUST/NEVER
- [ ] `scripts/validate_skill.py` run clean against the draft
- [ ] Tested against realistic prompts, not paraphrases of the spec — and against a no-skill baseline if possible
- [ ] Trigger checked against both should- and shouldn't-fire phrasings
- [ ] Placed in the right scope (project / personal / plugin) and checked against sibling skills for trigger collisions
