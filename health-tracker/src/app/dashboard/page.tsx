import { verifySession } from "@/lib/dal";
import { getHealthRecords, getGoals } from "@/lib/queries";
import { summarizeByMetric, goalProgress } from "@/lib/analysis";
import { deleteRecord } from "@/app/actions/records";
import { deleteGoal } from "@/app/actions/goals";
import { RecordForm } from "./RecordForm";
import { GoalForm } from "./GoalForm";
import { LogoutButton } from "./LogoutButton";

export default async function DashboardPage() {
  const session = await verifySession();
  const [records, goals] = await Promise.all([getHealthRecords(), getGoals()]);
  const summaries = summarizeByMetric(records);
  const goalsWithProgress = goalProgress(goals, records);

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-8 px-4 py-8">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Health Tracker</h1>
          <p className="text-sm text-gray-500">{session.email}</p>
        </div>
        <LogoutButton />
      </header>

      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-medium">Trends</h2>
        {summaries.length === 0 ? (
          <p className="text-sm text-gray-500">
            No records yet — add one below to see trends.
          </p>
        ) : (
          <ul className="grid grid-cols-2 gap-3">
            {summaries.map((s) => (
              <li key={s.metricType} className="rounded border p-3 text-sm">
                <div className="font-medium">{s.metricType.replaceAll("_", " ")}</div>
                <div>
                  Latest: {s.latest} {s.unit}{" "}
                  {s.trend === "up" ? "↑" : s.trend === "down" ? "↓" : "→"}
                </div>
                <div className="text-gray-500">
                  Avg: {s.average.toFixed(1)} {s.unit} ({s.count} entries)
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-medium">Goals</h2>
        {goalsWithProgress.length === 0 ? (
          <p className="text-sm text-gray-500">No goals set yet.</p>
        ) : (
          <ul className="flex flex-col gap-2">
            {goalsWithProgress.map((g) => (
              <li key={g.id} className="flex items-center justify-between rounded border p-3 text-sm">
                <div>
                  <div className="font-medium">{g.title}</div>
                  <div className="text-gray-500">
                    Target: {g.target_value} ({g.metric_type.replaceAll("_", " ")}) —{" "}
                    {g.progressPercent === null
                      ? "no data yet"
                      : `${g.progressPercent}% of target`}
                  </div>
                </div>
                <form action={deleteGoal.bind(null, g.id)}>
                  <button type="submit" className="text-red-600 underline">
                    Remove
                  </button>
                </form>
              </li>
            ))}
          </ul>
        )}
        <GoalForm />
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="text-lg font-medium">Records</h2>
        <RecordForm />
        <ul className="flex flex-col gap-2">
          {records.map((r) => (
            <li key={r.id} className="flex items-center justify-between rounded border p-3 text-sm">
              <div>
                <span className="font-medium">{r.metric_type.replaceAll("_", " ")}</span>{" "}
                {r.value} {r.unit} —{" "}
                <span className="text-gray-500">
                  {new Date(r.recorded_at).toLocaleString()}
                </span>
                {r.notes && <div className="text-gray-500">{r.notes}</div>}
              </div>
              <form action={deleteRecord.bind(null, r.id)}>
                <button type="submit" className="text-red-600 underline">
                  Delete
                </button>
              </form>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
