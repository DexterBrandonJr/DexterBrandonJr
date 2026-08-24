import type { HealthRecord, Goal } from "@/lib/queries";

export type MetricSummary = {
  metricType: string;
  latest: number;
  average: number;
  unit: string;
  count: number;
  trend: "up" | "down" | "flat";
};

export function summarizeByMetric(records: HealthRecord[]): MetricSummary[] {
  const byMetric = new Map<string, HealthRecord[]>();
  for (const record of records) {
    const list = byMetric.get(record.metric_type) ?? [];
    list.push(record);
    byMetric.set(record.metric_type, list);
  }

  return Array.from(byMetric.entries()).map(([metricType, entries]) => {
    // Records arrive newest-first from the query.
    const sorted = [...entries].sort(
      (a, b) => new Date(b.recorded_at).getTime() - new Date(a.recorded_at).getTime(),
    );
    const latest = sorted[0].value;
    const average = sorted.reduce((sum, r) => sum + r.value, 0) / sorted.length;
    const previous = sorted[1]?.value;
    let trend: MetricSummary["trend"] = "flat";
    if (previous !== undefined) {
      if (latest > previous) trend = "up";
      else if (latest < previous) trend = "down";
    }

    return {
      metricType,
      latest,
      average,
      unit: sorted[0].unit,
      count: sorted.length,
      trend,
    };
  });
}

export type GoalProgress = Goal & {
  latestValue: number | null;
  progressPercent: number | null;
};

export function goalProgress(goals: Goal[], records: HealthRecord[]): GoalProgress[] {
  const latestByMetric = new Map<string, number>();
  for (const record of records) {
    if (!latestByMetric.has(record.metric_type)) {
      latestByMetric.set(record.metric_type, record.value);
    }
  }

  return goals.map((goal) => {
    const latestValue = latestByMetric.get(goal.metric_type) ?? null;
    if (latestValue === null || goal.target_value === 0) {
      return { ...goal, latestValue, progressPercent: null };
    }
    const progressPercent = Math.max(
      0,
      Math.min(100, Math.round((latestValue / goal.target_value) * 100)),
    );
    return { ...goal, latestValue, progressPercent };
  });
}
