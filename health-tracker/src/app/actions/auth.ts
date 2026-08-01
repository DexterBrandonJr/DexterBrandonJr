"use server";

import { redirect } from "next/navigation";
import { AuthFormSchema, type AuthFormState } from "@/lib/definitions";
import { createClient } from "@/lib/supabase/server";

export async function signup(
  _state: AuthFormState,
  formData: FormData,
): Promise<AuthFormState> {
  const validatedFields = AuthFormSchema.safeParse({
    email: formData.get("email"),
    password: formData.get("password"),
  });

  if (!validatedFields.success) {
    return { errors: validatedFields.error.flatten().fieldErrors };
  }

  const { email, password } = validatedFields.data;
  const supabase = await createClient();
  const { error } = await supabase.auth.signUp({ email, password });

  if (error) {
    // Generic message — never confirm/deny whether an email is registered.
    return { message: "Could not create account. Please try again." };
  }

  return {
    message:
      "Account created. Check your email to confirm your address before signing in.",
  };
}

export async function login(
  _state: AuthFormState,
  formData: FormData,
): Promise<AuthFormState> {
  const validatedFields = AuthFormSchema.safeParse({
    email: formData.get("email"),
    password: formData.get("password"),
  });

  if (!validatedFields.success) {
    return { errors: validatedFields.error.flatten().fieldErrors };
  }

  const { email, password } = validatedFields.data;
  const supabase = await createClient();
  const { error } = await supabase.auth.signInWithPassword({
    email,
    password,
  });

  if (error) {
    return { message: "Invalid email or password." };
  }

  redirect("/dashboard");
}

export async function logout() {
  const supabase = await createClient();
  await supabase.auth.signOut();
  redirect("/login");
}
