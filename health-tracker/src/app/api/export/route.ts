import { verifySession } from "@/lib/dal";
import { getHealthRecords, getGoals } from "@/lib/queries";
import { toCsv } from "@/lib/csv";

export async function GET() {
  // verifySession() redirects unauthenticated callers; queries are already
  // scoped to the caller via the DAL + RLS, so this can only ever export
  // the signed-in user's own data.
  await verifySession();
  const [records, goals] = await Promise.all([getHealthRecords(), getGoals()]);

  const recordsCsv = toCsv(
    ["type", "metric_type", "value", "unit", "recorded_at", "notes"],
    records.map((r) => [
      "record",
      r.metric_type,
      r.value,
      r.unit,
      r.recorded_at,
      r.notes ?? "",
    ]),
  );

  const goalsCsv = toCsv(
    ["type", "title", "metric_type", "target_value", "target_date", "status"],
    goals.map((g) => [
      "goal",
      g.title,
      g.metric_type,
      g.target_value,
      g.target_date ?? "",
      g.status,
    ]),
  );

  const body = recordsCsv + "\r\n" + goalsCsv;
  const filename = `health-data-export-${new Date().toISOString().slice(0, 10)}.csv`;

  return new Response(body, {
    headers: {
      "Content-Type": "text/csv; charset=utf-8",
      "Content-Disposition": `attachment; filename="${filename}"`,
      // Personal health data — never let a CDN/proxy cache this response.
      "Cache-Control": "no-store",
    },
  });
}
