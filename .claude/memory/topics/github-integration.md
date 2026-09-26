# Github Integration

How repo creation works on this account, and which credential path actually has
the rights to do it. The short version: creating repos must go through the local
`gh` CLI, never the `github` MCP tool.

## 2026-09-05 — GitHub App cannot create personal-account repos (403) — use gh CLI

**Decisions:**
- Never use the `github` MCP `create_repository` tool for repos under the personal
  account. Use `gh repo create <name> --private` via Bash instead.
- Add a global rule to `~/.claude/CLAUDE.md` so every local session prefers `gh`:
  ```markdown
  ## GitHub
  Never use the `github` MCP `create_repository` tool — it authenticates as the
  Claude GitHub App, which cannot create repos on a personal account (403
  "Resource not accessible by integration"). Use `gh repo create` via Bash instead.
  ```

**Facts / preferences:**
- `POST /user/repos` is **not available to GitHub App installation tokens at all**.
  This is a platform limitation, not a permission anyone can grant — GitHub staff
  confirmed it in community discussion #171040 ("not supported with GitHub App
  tokens... you'd need to fall back to an OAuth App or a personal access token").
  Reconnecting or re-authorizing the integration will never fix it.
- Symptom to recognize instantly: `403 Resource not accessible by integration` on
  repo creation, while every other GitHub operation — reads, clones, pushes, PRs on
  existing repos — works fine. That asymmetry is the fingerprint.
- Token requirements if creating repos via API instead: classic PAT needs `repo`
  scope; fine-grained PAT needs `Administration: write` and is listed PAT-only.
- GitHub Apps **can** create *organization*-owned repos via
  `POST /orgs/{org}/repos` with `administration: write`. So moving work into a
  GitHub org would make `create_repository` work everywhere, including from
  cloud/web sessions that have no local `gh`. Not done — see open threads.
- Verified, not assumed: repos created in Aug 2026 were made **locally**. The
  initial commit carried the local git identity rather than
  `GitHub <noreply@github.com>` (so the repo was created empty and pushed to, not
  API-created with `autoInit`), and the commit message showed a local pre-commit
  hook had run. The working path was always local `gh`/git under the user's own
  OAuth token — never the Claude GitHub App.
- Neither Vercel nor Supabase was ever a repo-creation path. Vercel's
  `create_git_project` only *links* an already-existing repo, `deploy_to_vercel`
  bypasses git entirely, and Supabase creates databases, not repos.

**Open threads:**
- The global `~/.claude/CLAUDE.md` rule is **not yet applied**. Cloud/web sessions
  run in an isolated container with no access to the local machine, so this has to
  be done from a local Claude Code session or by hand.
- Undecided: whether to move repos into a GitHub org, which would be the durable
  fix that also works from cloud sessions. **Superseded — see the entry below.**
  `/web-setup` turned out to be the simpler, already-built answer to the same
  problem; the org route was never pursued to completion.

## 2026-09-05 — Resolved: /web-setup syncs local gh token to cloud sessions, fixes repo creation everywhere

**Decisions:**
- Fix adopted instead of the GitHub-org route: run `/web-setup` from a local,
  signed-in Claude Code session (not a raw shell command — it's a Claude Code
  slash command). It syncs the local `gh` CLI's own token to the Claude account,
  and every cloud session then authenticates to GitHub with that token instead of
  the Claude GitHub App.
- No org needed. This works from every surface with one command, run once — this
  chat, the mobile app, any future cloud session.

**Facts / preferences:**
- `/web-setup` requires being logged into claude.ai first (run `/login`). That is
  a *separate* login from GitHub, and its own error if skipped — "Not signed in
  to Claude. Run /login first." — is unrelated to the original 403 saga. This
  session and others were logged in to Claude the whole time; only `/web-setup`
  itself needed a fresh login.
- After `/web-setup` completed ("Connected as DexterBrandonJr. Opened
  https://claude.ai/code"), a fresh `create_repository` call in this cloud
  session succeeded immediately, with no `organization` parameter — created
  `DexterBrandonJr/claude-org-test-check-2` directly under the personal account.
- Confirms the root-cause theory from the entry above exactly: the blocker was
  specifically the GitHub App installation token, not "cloud sessions" as a
  category. Once a cloud session authenticates with the same personal token `gh`
  already uses locally, `POST /user/repos` succeeds there too, same as from the
  CLI.
- Source: Claude Code docs, "GitHub authentication options" — cloud sessions can
  connect via either the GitHub App or a token synced with `/web-setup`; either
  grants access to "any repository the connecting GitHub account can see, not
  just the repositories the Claude GitHub App is installed on."

**Artifacts:**
- PR: https://github.com/DexterBrandonJr/DexterBrandonJr/pull/7 (this record)
- The fix was confirmed live by creating `claude-org-test-check-2` via
  `create_repository` with no `organization` param, immediately after
  `/web-setup`. Deleted afterward as a throwaway — the confirmation is recorded
  here, not in a repo that has to keep existing to prove it.

**Open threads:**
- The `brand841` GitHub org created while chasing the org route is unused and can
  stay parked, or be repurposed later — it's no longer needed for this.
- The `~/.claude/CLAUDE.md` rule from the entry above is lower-priority now that
  `create_repository` genuinely works post-`/web-setup`, but worth keeping as a
  fallback note in case the sync ever lapses.

## 2026-09-16 — The draft-to-ready flip is GraphQL and has its own rate limit

**Decisions:** When `update_pull_request` with `draft: false` fails with
"API rate limit already exceeded" while every other call succeeds, the
limit is on GitHub's GraphQL API, not REST. Creating, closing, retitling
and merging a pull request are REST and kept working the whole time; the
draft→ready conversion is the one GraphQL mutation in the flow. Confirmed
the diagnosis by calling the REST merge endpoint on the draft: it reached
GitHub and answered `405 Pull Request is still a draft` — a real refusal,
not a limit.

The way through is REST-only: close the draft, create a new pull request
from the same branch with `draft: false`, merge. Used it three times in one
evening, each time because the version already on `main` was wrong and was
being shared; declined it for documentation nobody was waiting on and armed
a check-in instead. The cost is a dead PR number in the history; the rule
is to pay it only when the stale version being live costs more.

**Facts / preferences:**
- The GraphQL limit lasted well over an hour and returned twice in one
  evening. It cleared on its own; no retry pattern changed its timing.
- Retrying a limited write does not help and may extend the block. Reads
  say nothing about whether writes are limited — separate budgets.
- A first call that sets title, body and `draft` together can apply the
  REST fields and then fail on the GraphQL one, so a PR can end up retitled
  but still a draft. Read it back before assuming either state.
- Opening pull requests non-draft in the first place avoids the flip
  entirely; the session's own rule is to open them as drafts, so the flip
  is on the path every time.

**Artifacts:** `DexterBrandonJr/trading-engine` pull requests 148→149 and
this repo's 27→28 and 29→30 are the close-and-recreate pairs.

## 2026-09-26 — The draft-to-ready flip worked; send it alone

**Decisions:** Flipped [DexterBrandonJr#32](https://github.com/DexterBrandonJr/DexterBrandonJr/pull/32) from draft to ready for review with `update_pull_request` and `draft: false`, and it went through first try. No rate limit, so the close-and-recreate workaround was not needed and the pull request number stayed intact. Sent `draft: false` on its own, with no title or body in the same call — deliberately, because of the partial-application trap in the entry above: one call carrying both can apply the REST fields and then fail on the GraphQL one, leaving a pull request retitled but still a draft. Read the state back afterwards rather than trusting the empty-looking success.

**Facts / preferences:** The GraphQL rate limit is **intermittent, not a standing condition**. It blocked this same operation repeatedly on 2026-09-16 and was completely clear ten days later. So the order of preference is: try the flip alone first, read back to confirm, and only reach for close-and-recreate if it actually fails *and* the stale version being live is costing something. Do not skip straight to the workaround on the strength of the earlier entry.

**Artifacts:** Pull request 32 — flipped 2026-09-16 15:34 UTC, confirmed `draft: false` and `mergeable_state: clean` by reading it back. No close-and-recreate pair this time, unlike 148→149, 27→28 and 29→30.

**Open threads:** None. The two paths are now both recorded with the condition that picks between them.
