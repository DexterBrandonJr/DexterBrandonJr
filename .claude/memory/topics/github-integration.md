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
  fix that also works from cloud sessions.
