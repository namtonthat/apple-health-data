import { Card } from "@tremor/react";
import { dashboard, fmt, shortDate, type Num } from "@/lib/data";

export function Training() {
  const { e1rm, prs, workouts, strava } = dashboard;

  // Current estimated 1RM = most recent row of the rolling-total series.
  const cur = e1rm.length ? e1rm[e1rm.length - 1] : ({} as (typeof e1rm)[number]);

  const lifts: { lift: string; e: Num; pr: Num }[] = [
    { lift: "Squat", e: cur.squat_e1rm ?? null, pr: prs.squat_pr_kg as Num },
    { lift: "Bench", e: cur.bench_e1rm ?? null, pr: prs.bench_pr_kg as Num },
    { lift: "Deadlift", e: cur.deadlift_e1rm ?? null, pr: prs.deadlift_pr_kg as Num },
    { lift: "Total", e: cur.estimated_total ?? null, pr: prs.total_pr_kg as Num },
  ];

  const diffOf = (e: Num, pr: Num): number | null =>
    e !== null && pr !== null ? Math.round((e as number) - (pr as number)) : null;

  const signed = (n: number) => `${n >= 0 ? "+" : ""}${n}`;

  return (
    <div className="space-y-3">
      {/* ── Lifts: current e1RM vs competition PR (the centerpiece) ── */}
      <Card className="p-4">
        <div className="mb-3 flex items-baseline justify-between">
          <p className="text-tremor-default font-medium text-white">Lifts</p>
          <p className="text-tremor-label text-gray-500">
            e1RM vs comp PR{cur.workout_date ? ` · ${shortDate(cur.workout_date)}` : ""}
          </p>
        </div>

        <div className="grid grid-cols-2 gap-2">
          {lifts.map((l) => {
            const diff = diffOf(l.e, l.pr);
            const tone =
              diff === null
                ? "text-gray-500"
                : diff >= 0
                  ? "text-emerald-400"
                  : "text-rose-400";
            const total = l.lift === "Total";
            return (
              <div
                key={l.lift}
                className={`rounded-tremor-default border p-3 ${
                  total
                    ? "col-span-2 border-gray-700 bg-gray-900/60"
                    : "border-gray-800 bg-gray-900/30"
                }`}
              >
                <div className="flex items-center justify-between">
                  <p className="text-tremor-label uppercase tracking-wide text-gray-400">
                    {l.lift}
                  </p>
                  <span className={`text-tremor-label font-medium ${tone}`}>
                    {diff === null ? "-" : signed(diff)}
                  </span>
                </div>
                <p className="mt-1 text-2xl font-semibold text-white">
                  {fmt(l.e, 0)}
                  <span className="text-tremor-label font-normal text-gray-500"> kg</span>
                </p>
                <p className="text-tremor-label text-gray-500">PR {fmt(l.pr, 0, " kg")}</p>
              </div>
            );
          })}
        </div>
      </Card>

      {/* ── Competition context ── */}
      <Card className="p-4">
        <p className="mb-3 text-tremor-default font-medium text-white">Competition</p>
        <div className="grid grid-cols-3 gap-3">
          <div>
            <p className="text-tremor-label text-gray-500">Best DOTS</p>
            <p className="mt-0.5 text-xl font-semibold text-white">
              {fmt(prs.best_dots as Num, 1)}
            </p>
          </div>
          <div>
            <p className="text-tremor-label text-gray-500">Meets</p>
            <p className="mt-0.5 text-xl font-semibold text-white">
              {fmt(prs.total_competitions as Num, 0)}
            </p>
          </div>
          <div>
            <p className="text-tremor-label text-gray-500">Best place</p>
            <p className="mt-0.5 text-xl font-semibold text-white">
              {prs.best_place != null ? String(prs.best_place) : "-"}
            </p>
          </div>
        </div>
        {prs.last_competition != null && (
          <p className="mt-3 border-t border-gray-800 pt-2 text-tremor-label text-gray-500">
            Last meet · {shortDate(String(prs.last_competition))}
          </p>
        )}
      </Card>

      {/* ── Recent workouts ── */}
      <Card className="p-4">
        <p className="mb-2 text-tremor-default font-medium text-white">Recent workouts</p>
        <div className="divide-y divide-gray-800">
          {workouts.slice(0, 8).map((w, i) => (
            <div key={i} className="flex items-center justify-between gap-3 py-2">
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

      {/* ── Cardio ── */}
      {strava.length > 0 && (
        <Card className="p-4">
          <p className="mb-2 text-tremor-default font-medium text-white">Cardio (Strava)</p>
          <div className="divide-y divide-gray-800">
            {strava.slice(0, 6).map((a, i) => (
              <div key={i} className="flex items-center justify-between gap-3 py-2">
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
