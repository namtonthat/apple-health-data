import { Card, LineChart } from "@tremor/react";
import { ChartCard } from "@/components/ChartCard";
import { dashboard, fmt, lastN, shortDate } from "@/lib/data";

export function Training() {
  const { e1rm, prs, workouts, strava } = dashboard;

  const e1rmSeries = lastN(
    e1rm.filter((r) => r.estimated_total != null),
    60,
  ).map((r) => ({
    date: shortDate(r.workout_date),
    Squat: r.squat_e1rm,
    Bench: r.bench_e1rm,
    Deadlift: r.deadlift_e1rm,
  }));

  const prCards = [
    { label: "Squat", value: prs.squat_pr_kg },
    { label: "Bench", value: prs.bench_pr_kg },
    { label: "Deadlift", value: prs.deadlift_pr_kg },
    { label: "Total", value: prs.total_pr_kg },
  ];

  return (
    <div className="space-y-3">
      <ChartCard title="Estimated 1RM" subtitle="Big 3 · recent sessions">
        <LineChart
          data={e1rmSeries}
          index="date"
          categories={["Squat", "Bench", "Deadlift"]}
          colors={["emerald", "blue", "amber"]}
          showLegend
          startEndOnly
          connectNulls
          autoMinValue
          className="h-44"
        />
      </ChartCard>

      <Card className="p-4">
        <p className="text-tremor-default font-medium text-white">Competition PRs</p>
        <p className="text-tremor-label text-gray-500">
          Best DOTS {fmt(prs.best_dots as number, 1)} · {prs.total_competitions} meets
        </p>
        <div className="mt-3 grid grid-cols-4 gap-2">
          {prCards.map((p) => (
            <div key={p.label} className="rounded-tremor-default bg-gray-900 p-2 text-center">
              <p className="text-lg font-semibold text-white">{fmt(p.value as number, 0)}</p>
              <p className="text-tremor-label text-gray-500">{p.label}</p>
            </div>
          ))}
        </div>
      </Card>

      <Card className="p-4">
        <p className="mb-2 text-tremor-default font-medium text-white">Recent workouts</p>
        <div className="divide-y divide-gray-800">
          {workouts.slice(0, 8).map((w, i) => (
            <div key={i} className="flex items-center justify-between py-2">
              <div className="min-w-0">
                <p className="truncate text-sm text-gray-200">{w.workout_name}</p>
                <p className="text-tremor-label text-gray-500">
                  {shortDate(w.workout_date)} · {fmt(w.workout_duration_minutes, 0, "m")} ·{" "}
                  {fmt(w.total_sets, 0)} sets
                </p>
              </div>
              <p className="shrink-0 text-sm font-medium text-gray-300">
                {fmt(w.total_volume_kg ? w.total_volume_kg / 1000 : null, 1, "t")}
              </p>
            </div>
          ))}
        </div>
      </Card>

      {strava.length > 0 && (
        <Card className="p-4">
          <p className="mb-2 text-tremor-default font-medium text-white">Cardio (Strava)</p>
          <div className="divide-y divide-gray-800">
            {strava.slice(0, 6).map((a, i) => (
              <div key={i} className="flex items-center justify-between py-2">
                <div className="min-w-0">
                  <p className="truncate text-sm text-gray-200">{a.activity_name}</p>
                  <p className="text-tremor-label text-gray-500">
                    {shortDate(a.activity_date)} · {a.activity_type}
                  </p>
                </div>
                <p className="shrink-0 text-sm font-medium text-gray-300">
                  {fmt(a.distance_km, 1, "km")}
                </p>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
