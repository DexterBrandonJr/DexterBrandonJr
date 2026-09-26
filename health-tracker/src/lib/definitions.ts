import * as z from "zod";

export const AuthFormSchema = z.object({
  email: z.email({ error: "Enter a valid email address." }).trim(),
  password: z
    .string()
    .min(8, { error: "Password must be at least 8 characters." })
    .regex(/[a-zA-Z]/, { error: "Password must contain a letter." })
    .regex(/[0-9]/, { error: "Password must contain a number." }),
});

export type AuthFormState =
  | { errors?: { email?: string[]; password?: string[] }; message?: string }
  | undefined;

const METRIC_TYPES = [
  "weight",
  "blood_pressure_systolic",
  "blood_pressure_diastolic",
  "resting_heart_rate",
  "blood_glucose",
  "sleep_hours",
  "steps",
  "other",
] as const;

export const HealthRecordSchema = z.object({
  metricType: z.enum(METRIC_TYPES, { error: "Choose a valid metric." }),
  value: z.coerce.number().finite().safe(),
  unit: z.string().trim().min(1).max(16),
  recordedAt: z.coerce.date(),
  notes: z.string().trim().max(2000).optional().or(z.literal("")),
});

export type HealthRecordFormState =
  | { errors?: Record<string, string[]>; message?: string }
  | undefined;

export const GoalSchema = z.object({
  title: z.string().trim().min(1).max(200),
  metricType: z.enum(METRIC_TYPES, { error: "Choose a valid metric." }),
  targetValue: z.coerce.number().finite().safe(),
  targetDate: z.coerce.date().optional(),
});

export type GoalFormState =
  | { errors?: Record<string, string[]>; message?: string }
  | undefined;

export { METRIC_TYPES };
