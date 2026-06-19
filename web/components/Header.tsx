import { ProgressCircle } from "@tremor/react";
import { dashboard, fmt, shortDate } from "@/lib/data";

function readinessColor(score: number): string {
  if (score >= 80) return "emerald";
  if (score >= 60) return "amber";
  return "rose";
}

export function Header() {
  const score = dashboard.latest.readiness_score ?? null;
  const color = score !== null ? readinessColor(score) : "slate";

  return (
    <header className="flex items-center gap-4 px-5 pb-4 pt-6">
      <ProgressCircle value={score ?? 0} radius={34} strokeWidth={7} color={color}>
        <span className="text-lg font-semibold text-white">{fmt(score)}</span>
      </ProgressCircle>
      <div className="min-w-0">
        <p className="text-xs uppercase tracking-wide text-gray-500">Readiness</p>
        <h1 className="truncate text-xl font-semibold text-white">
          {dashboard.user_name.split(" ")[0]}&rsquo;s vitals
        </h1>
        <p className="text-xs text-gray-500">
          as of {shortDate(dashboard.last_data_date)}
        </p>
      </div>
    </header>
  );
}
