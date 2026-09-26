# Security model

This app stores personal health data, so it's built with a strict default-deny
posture. No system connected to the internet is unhackable — this document
describes the layers in place, not a guarantee.

## Data isolation

- **Row Level Security (RLS)** is enabled and *forced* (`force row level
  security`) on every table in `supabase/migrations/`. Every policy checks
  `auth.uid() = user_id`. Even a bug in application code, or a compromised
  API key, cannot read or write another user's rows — Postgres itself
  refuses the query.
- The Postgres schema, RLS policies, and Supabase Auth are the actual
  security boundary. Everything else below is defense in depth.

## AuthN / AuthZ

- Authentication is handled entirely by Supabase Auth (email + password,
  managed sessions, rate limiting, breached-password checks) rather than a
  hand-rolled implementation.
- `src/lib/dal.ts` (`verifySession`) is the single Data Access Layer choke
  point. It calls `supabase.auth.getUser()`, which re-validates the session
  against Supabase — not just trusting a cookie — before any query runs.
- `src/proxy.ts` (Next.js 16's renamed Middleware) only does an *optimistic*
  redirect for unauthenticated users on protected paths. It is not the
  security boundary — `verifySession()` + RLS are.
- All server actions and data queries call `verifySession()` first and use
  the session's `userId` for writes — the client never supplies `user_id`.

## Secrets

- `NEXT_PUBLIC_SUPABASE_ANON_KEY` is safe to expose to the browser by
  design (Supabase enforces RLS on every request that uses it).
- The Supabase **service role key** (which bypasses RLS) is never used by
  this app. If you ever add an admin/background job that needs it, keep it
  server-only, never `NEXT_PUBLIC_`-prefixed, and audit every use.
- `.env.local` (real secrets) is gitignored. Only `.env.example`
  (placeholders) is committed.

## Transport / browser hardening

Configured in `next.config.ts`:
- Strict `Content-Security-Policy` (no inline scripts, no third-party
  script/frame origins, `frame-ancestors 'none'`).
- `Strict-Transport-Security`, `X-Frame-Options: DENY`,
  `X-Content-Type-Options: nosniff`, restrictive `Permissions-Policy`.

## CSRF

Next.js Server Actions verify the request's `Origin` against `Host` and
reject mismatches automatically — no extra CSRF token plumbing needed. If
you put this behind a reverse proxy or CDN on a different origin, configure
`serverActions.allowedOrigins` in `next.config.ts` accordingly.

## Input validation

All form input is validated server-side with `zod` schemas
(`src/lib/definitions.ts`) before it touches the database — enums for
metric types, length/finite-number bounds, etc. Client-side validation is
UX only; the server never trusts it.

## Known accepted risk

`npm audit` flags `postcss`/`sharp` versions bundled *inside* `next`
itself (present in every current Next.js release, not something this
project's `package.json` controls). Not exploitable here since the app
never processes attacker-supplied CSS or images. Re-check
`npm audit` when upgrading Next.

## Not yet implemented (recommended next steps)

- Multi-factor authentication (Supabase Auth supports TOTP MFA — worth
  enabling for real health data).
- Field-level encryption for particularly sensitive values, if you go
  beyond personal use.
- Automated dependency scanning (Dependabot / `npm audit` in CI).
- A privacy policy / data deletion flow if this is ever used by more than
  one person.
