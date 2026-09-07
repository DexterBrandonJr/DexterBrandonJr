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
