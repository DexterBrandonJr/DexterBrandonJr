import "server-only";
import { verifySession } from "@/lib/dal";
import { createClient } from "@/lib/supabase/server";

export type HealthRecord = {
  id: string;
  metric_type: string;
  value: number;
  unit: string;
  recorded_at: string;
  notes: string | null;
};

export type Goal = {
  id: string;
  title: string;
  metric_type: string;
  target_value: number;
  target_date: string | null;
  status: "active" | "achieved" | "abandoned";
};

// RLS already restricts rows to auth.uid(), but verifySession() is called
// first so unauthenticated requests never reach the database at all.
export async function getHealthRecords(): Promise<HealthRecord[]> {
  await verifySession();
  const supabase = await createClient();
  const { data, error } = await supabase
    .from("health_records")
    .select("id, metric_type, value, unit, recorded_at, notes")
    .order("recorded_at", { ascending: false })
    .limit(200);

  if (error) throw new Error("Failed to load health records.");
  return data;
}

export async function getGoals(): Promise<Goal[]> {
  await verifySession();
  const supabase = await createClient();
  const { data, error } = await supabase
    .from("goals")
    .select("id, title, metric_type, target_value, target_date, status")
    .order("created_at", { ascending: false });

  if (error) throw new Error("Failed to load goals.");
  return data;
}
