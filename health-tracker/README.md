# Health Tracker

Privately track personal health records and goals. Next.js 16 (App Router) +
Supabase (Postgres, Auth, Row Level Security). See `SECURITY.md` for the
security model — RLS is the real data boundary, not app code.

## Setup

1. **Create a Supabase project** at https://supabase.com/dashboard (free
   tier is fine to start).
2. **Run the migration**: in the Supabase dashboard, open the SQL editor
   and run the contents of `supabase/migrations/0001_health_records_and_goals.sql`
   (or use the Supabase CLI: `supabase db push`).
3. **Copy env vars**: `cp .env.example .env.local`, then fill in
   `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` from
   Project Settings > API in the Supabase dashboard. Never commit
   `.env.local`.
4. **Install and run**:
   ```bash
   npm install
   npm run dev
   ```
   Open http://localhost:3000, sign up, confirm your email (Supabase sends
   a confirmation link by default), then sign in.

## Deploying

Deploy to Vercel (or any Next.js host): set the same two env vars in the
project's environment settings, then deploy. No other config needed —
Supabase Auth handles sessions, RLS handles per-user data isolation.

## Structure

- `src/proxy.ts` — optimistic auth redirect (Next.js 16 renamed Middleware
  to Proxy; functionality is the same).
- `src/lib/dal.ts` — `verifySession()`, the single choke point that
  re-validates every session against Supabase before any data access.
- `src/lib/queries.ts` / `src/app/actions/*.ts` — reads and writes, all
  routed through `verifySession()`.
- `src/lib/definitions.ts` — zod validation schemas.
- `supabase/migrations/` — SQL schema + RLS policies.

## Learn more

- [Next.js Documentation](https://nextjs.org/docs)
- [Supabase Documentation](https://supabase.com/docs)
