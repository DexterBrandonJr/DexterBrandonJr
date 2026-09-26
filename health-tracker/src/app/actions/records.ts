"use server";

import { revalidatePath } from "next/cache";
import { verifySession } from "@/lib/dal";
import { HealthRecordSchema, type HealthRecordFormState } from "@/lib/definitions";
import { createClient } from "@/lib/supabase/server";

export async function addRecord(
  _state: HealthRecordFormState,
  formData: FormData,
): Promise<HealthRecordFormState> {
  const session = await verifySession();

  const validated = HealthRecordSchema.safeParse({
    metricType: formData.get("metricType"),
    value: formData.get("value"),
    unit: formData.get("unit"),
    recordedAt: formData.get("recordedAt") || new Date(),
    notes: formData.get("notes"),
  });

  if (!validated.success) {
    return { errors: validated.error.flatten().fieldErrors };
  }

  const { metricType, value, unit, recordedAt, notes } = validated.data;
  const supabase = await createClient();

  // user_id is always taken from the verified session, never from client
  // input — RLS would reject a mismatched user_id anyway, but this avoids
  // even attempting a write with an untrusted value.
  const { error } = await supabase.from("health_records").insert({
    user_id: session.userId,
    metric_type: metricType,
    value,
    unit,
    recorded_at: recordedAt.toISOString(),
    notes: notes || null,
  });

  if (error) {
    return { message: "Failed to save record. Please try again." };
  }

  revalidatePath("/dashboard");
  return { message: "Record saved." };
}

export async function deleteRecord(recordId: string) {
  const session = await verifySession();
  const supabase = await createClient();

  const { error } = await supabase
    .from("health_records")
    .delete()
    .eq("id", recordId)
    .eq("user_id", session.userId);

  if (error) throw new Error("Failed to delete record.");
  revalidatePath("/dashboard");
}
