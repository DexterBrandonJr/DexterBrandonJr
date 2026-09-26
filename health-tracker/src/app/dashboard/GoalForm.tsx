"use client";

import { useActionState } from "react";
import { addGoal } from "@/app/actions/goals";
import { METRIC_TYPES } from "@/lib/definitions";

export function GoalForm() {
  const [state, action, pending] = useActionState(addGoal, undefined);

  return (
    <form action={action} className="flex flex-col gap-3 rounded border p-4">
      <h2 className="font-medium">Set a goal</h2>
      <input
        name="title"
        placeholder="Goal title (e.g. Lower resting heart rate)"
        required
        className="rounded border px-2 py-2"
      />
      <div className="grid grid-cols-3 gap-3">
        <select name="metricType" required className="rounded border px-2 py-2">
          {METRIC_TYPES.map((metric) => (
            <option key={metric} value={metric}>
              {metric.replaceAll("_", " ")}
            </option>
          ))}
        </select>
        <input
          name="targetValue"
          type="number"
          step="any"
          placeholder="target value"
          required
          className="rounded border px-2 py-2"
        />
        <input name="targetDate" type="date" className="rounded border px-2 py-2" />
      </div>
      {state?.message && <p className="text-sm">{state.message}</p>}
      <button
        type="submit"
        disabled={pending}
        className="self-start rounded bg-black px-4 py-2 text-white disabled:opacity-50"
      >
        {pending ? "Saving..." : "Add goal"}
      </button>
    </form>
  );
}
