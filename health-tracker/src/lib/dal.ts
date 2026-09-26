import "server-only";
import { cache } from "react";
import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";

// Verifies the session against Supabase (a real network/DB check via
// auth.getUser(), not just trusting the cookie) so every caller gets an
// authoritative answer. cache() dedupes repeat calls within one render pass.
export const verifySession = cache(async () => {
  const supabase = await createClient();
  const {
    data: { user },
    error,
  } = await supabase.auth.getUser();

  if (error || !user) {
    redirect("/login");
  }

  return { isAuth: true, userId: user.id, email: user.email };
});
