"use server";

import { revalidatePath } from "next/cache";
import { verifySession } from "@/lib/dal";
import { GoalSchema, type GoalFormState } from "@/lib/definitions";
import { createClient } from "@/lib/supabase/server";

export async function addGoal(
  _state: GoalFormState,
  formData: FormData,
): Promise<GoalFormState> {
  const session = await verifySession();

  const validated = GoalSchema.safeParse({
    title: formData.get("title"),
    metricType: formData.get("metricType"),
    targetValue: formData.get("targetValue"),
    targetDate: formData.get("targetDate") || undefined,
  });

  if (!validated.success) {
    return { errors: validated.error.flatten().fieldErrors };
  }

  const { title, metricType, targetValue, targetDate } = validated.data;
  const supabase = await createClient();

  const { error } = await supabase.from("goals").insert({
    user_id: session.userId,
    title,
    metric_type: metricType,
    target_value: targetValue,
    target_date: targetDate ? targetDate.toISOString().slice(0, 10) : null,
  });

  if (error) {
    return { message: "Failed to save goal. Please try again." };
  }

  revalidatePath("/dashboard");
  return { message: "Goal saved." };
}

export async function updateGoalStatus(
  goalId: string,
  status: "active" | "achieved" | "abandoned",
) {
  const session = await verifySession();
  const supabase = await createClient();

  const { error } = await supabase
    .from("goals")
    .update({ status })
    .eq("id", goalId)
    .eq("user_id", session.userId);

  if (error) throw new Error("Failed to update goal.");
  revalidatePath("/dashboard");
}

export async function deleteGoal(goalId: string) {
  const session = await verifySession();
  const supabase = await createClient();

  const { error } = await supabase
    .from("goals")
    .delete()
    .eq("id", goalId)
    .eq("user_id", session.userId);

  if (error) throw new Error("Failed to delete goal.");
  revalidatePath("/dashboard");
}
