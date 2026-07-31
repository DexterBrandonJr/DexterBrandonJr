"use client";

import { useActionState } from "react";
import { addRecord } from "@/app/actions/records";
import { METRIC_TYPES } from "@/lib/definitions";

export function RecordForm() {
  const [state, action, pending] = useActionState(addRecord, undefined);

  return (
    <form action={action} className="flex flex-col gap-3 rounded border p-4">
      <h2 className="font-medium">Log a health record</h2>
      <div className="grid grid-cols-2 gap-3">
        <select name="metricType" required className="rounded border px-2 py-2">
          {METRIC_TYPES.map((metric) => (
            <option key={metric} value={metric}>
              {metric.replaceAll("_", " ")}
            </option>
          ))}
        </select>
        <input
          name="unit"
          placeholder="unit (e.g. lb, bpm, hrs)"
          required
          className="rounded border px-2 py-2"
        />
        <input
          name="value"
          type="number"
          step="any"
          placeholder="value"
          required
          className="rounded border px-2 py-2"
        />
        <input
          name="recordedAt"
          type="datetime-local"
          className="rounded border px-2 py-2"
        />
      </div>
      <textarea
        name="notes"
        placeholder="notes (optional)"
        maxLength={2000}
        className="rounded border px-2 py-2"
      />
      {state?.message && <p className="text-sm">{state.message}</p>}
      <button
        type="submit"
        disabled={pending}
        className="self-start rounded bg-black px-4 py-2 text-white disabled:opacity-50"
      >
        {pending ? "Saving..." : "Add record"}
      </button>
    </form>
  );
}
