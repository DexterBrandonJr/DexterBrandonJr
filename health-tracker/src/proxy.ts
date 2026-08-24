import { type NextRequest } from "next/server";
import { updateSession } from "@/lib/supabase/proxy";

// Optimistic auth check only (Next.js 16 Proxy convention, formerly Middleware).
// Real authorization happens per-request in the DAL (src/lib/dal.ts) and via
// Supabase Row Level Security — this just pre-filters unauthenticated users.
export async function proxy(request: NextRequest) {
  return updateSession(request);
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
