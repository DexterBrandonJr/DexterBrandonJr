---
name: innovation-brief
description: Produces a sourced, visual, ADHD-friendly innovation brief for a build idea before anything is built — an honest map of what can be done today (each claim tiered Proven / Tested / Expected, verified against the tools and repos actually in reach), what the field shipped recently and who is doing it, the history, the psychology / probability / habit lenses, the ideas that go past the field, and the first three moves — delivered as a published artifact page plus a short chat reply. Use it whenever Dex asks to "brainstorm", "do deep research", "think through all the ways", "is this really the most innovative / efficient way", "give me a visual breakdown", "mind maps and diagrams", "what's being done currently", "use psychology / probability / statistics", or wants to be convinced a build is worth starting — even when he never says "research" — and before a workhorse blueprint is filled. Not for building the thing (that is workhorse and phased-build) and not for a plain factual question that one search answers.
---

# Innovation brief

A brief exists to turn "I'm sure there's a better way" into a page Dex can hold: what is true today, what the field is doing, what would actually be new, and the first three moves. It is the research step of the workhorse rhythm (DOCTRINE §2, step 1) made repeatable, and it has to land in a form that motivates rather than overwhelms.

Two failure modes it is built to prevent. The first is the reflex answer — a design from memory with no proof that its pieces exist on his account. The second is the wall of text — thorough, correct, and never read. Everything below is aimed at those two.

## 1. Frame it in two sentences

Write the question as one sentence and, as a second sentence, what would make the answer a gimmick. Example: *"Every Claude he talks to is a client with no shared storage. A gimmick would be another notes app he has to remember to open."* Keep both sentences; they become the page's first tile and the standard every idea is judged against.

## 2. Prove what is in reach before reading anything

Claims about capability are tiered, and a tier is earned, not assigned. Before the web:

- `ListConnectors` — what his phone, Cowork and Code sessions can all reach. A hub that only one surface can see is not a hub.
- Try the tool. If the design says "the artifacts can be read", list them and read one. If it says "transcripts are on disk", `ls` the directory. One real call turns an Expected into a Proven and costs seconds.
- Read the repos that already touch the problem (`.claude/memory/`, prior blueprints, prior artifacts via the Artifact tool's `list` and `read`).

Record each finding with its tier as you go. The capability map on the page is written from this list, never from recall.

## 3. Scan the field

Four to six `WebSearch` calls, chosen to cover four things: the vendor's own docs (what the product does this month), what shipped in the last ninety days, the open-source and indie builders (GitHub, Product Hunt, personal blogs), and the history (who had the idea first, what changed). Prefer primary sources — help centers, platform docs, the repo — over roundups. Every fact that reaches the page carries its link in the Sources section; the page is only as strong as a reader's ability to check it.

Reading the results, look for the property table: the three to five properties that matter for Dex's use (phone-first, zero server, works across surfaces, measures itself, decays on purpose — whatever this build turns on) and which existing approach has which. The innovation usually lives in the combination nobody has shipped, and the table is how that becomes visible instead of asserted.

## 4. Run the lenses

`references/lenses.md` holds the question bank. The four that always apply:

- **Psychology** — which known effect does each design piece rely on (extended mind, transactive memory, Zeigarnik, cue-dependent recall, working-memory load, implementation intentions, spacing)? Name the effect and the researcher; never invent a statistic.
- **Probability and statistics** — write the cost or the benefit as an expected value with named variables (`p × c`), give an illustrative number clearly marked as illustrative, and say which measured number replaces it later.
- **Habits** — what is the one trigger and the one action (cue → routine), and what removes the willpower from it?
- **Systems** — the eight workhorse parts, derived for this build (record, gate, loop, surfaces, scorer, review, counterfactual, stages). A brief that cannot name the scorer is proposing a gimmick.

## 5. Name what would be new, with tiers

List the ideas that go past the field — usually three to six — and tier each honestly. "Proven capability, Expected as a workflow" is a legitimate and common tier. Present the field's best ideas as things to steal by name (Karpathy's wiki, Letta's tiers, mem0's extraction) so Dex learns the landscape while reading the design.

## 6. Build the page

Author an HTML artifact from `assets/brief-skeleton.html` (load the `artifact-design` and `artifact-diagramming` skills first; `dataviz` if any chart carries real numbers). The section order is fixed because it is the order he reads in:

1. **Six tiles** — the whole answer on one screen: the answer, the shape, what's new, what it costs now, his machines, what is needed from him.
2. **The honest capability map** — a table: source or claim, mechanism, tier chip.
3. **The mechanism** — one inline SVG showing where data flows and which parts talk; arrows labeled.
4. **The mind map** — one inline SVG, the center and its branches, each branch with two leaves.
5. **The math** — the expected-value paragraph and one drawn-to-scale figure if a curve carries the argument.
6. **The lenses table** — effect, what it says, where it lives in the design.
7. **The field table** and the new ideas with tiers.
8. **History** — a dated list, oldest first.
9. **Vocabulary** — eight terms, one line each, so he can argue the design with anyone.
10. **First three moves** — each one usable the day it lands, and what each gives him.
11. **Sources**.

Rules that keep it readable: short lines; one claim per figure with a caption that states it; tiers as chips, not prose; deep material behind `<details>`; no section longer than a phone screen without a figure or a table breaking it. Publish with a two-to-four-word name, never a title with a colon.

## 7. Deliver

The chat reply is short: the two or three findings that change the picture, the link, and the one decision he has to make (a name, a go). The page carries the depth. End with the standing summary block (short lines, the payload at the bottom).

## 8. Deposit

Before ending: a memory entry (public-safe in the coordination repo; personal or project detail in the private repo), and if the brief revealed a rule about how to work — a research source that always pays, a lens that caught something — put it in this skill's references, not in the memory. The next brief should start further along than this one did.

## Quick checklist

- [ ] Two-sentence frame written, gimmick named
- [ ] Connectors listed; at least one capability proven by a real call
- [ ] 4–6 searches, primary sources, every page fact linked
- [ ] Property table drafted from the field, not asserted
- [ ] Four lenses run; effects named with their researchers
- [ ] New ideas listed with honest tiers
- [ ] Page in the fixed order, six tiles first, figures captioned
- [ ] Short reply, link, one decision, summary block
- [ ] Memory deposited; skill references updated if a lesson surfaced
