import { Kpi } from "@/components/Kpi";
import { dashboard, fmt, goalStatus, series, type Num } from "@/lib/data";

type Dir = "higher" | "lower" | "target";

interface MetricDef {
  label: string;
  key: string;
  goalKey?: string;
  unit?: string;
  digits?: number;
  dir?: Dir;
  color?: string;
  sparkDays?: number;
}

const METRICS: MetricDef[] = [
  { label: "Sleep", key: "sleep_hours", goalKey: "sleep_hours", unit: "h", digits: 1, dir: "higher", color: "indigo" },
  { label: "HRV", key: "hrv_ms", goalKey: "hrv_ms", unit: "ms", dir: "higher", color: "violet" },
  { label: "Resting HR", key: "resting_hr_bpm", goalKey: "resting_hr_bpm", unit: "", dir: "lower", color: "rose" },
  { label: "Steps", key: "steps", goalKey: "steps", unit: "", dir: "higher", color: "cyan" },
  { label: "Weight", key: "weight_kg", goalKey: "weight_kg", unit: "kg", digits: 1, dir: "lower", color: "emerald", sparkDays: 30 },
  { label: "Protein", key: "protein_g", goalKey: "protein_g", unit: "g", dir: "higher", color: "amber" },
];

export function Overview() {
  const { latest, goals } = dashboard;
  return (
    <div className="grid grid-cols-2 gap-3">
      {METRICS.map((m) => {
        const value = latest[m.key] as Num;
        const goal = m.goalKey ? goals[m.goalKey] : undefined;
        const status = goalStatus(value, goal, m.dir ?? "higher");
        return (
          <Kpi
            key={m.key}
            label={m.label}
            value={fmt(value, m.digits ?? 0, m.unit)}
            sub={goal ? `goal ${fmt(goal, m.digits ?? 0, m.unit)}` : undefined}
            delta={status ? { pct: status.pct, above: status.above, tone: status.tone } : null}
            spark={series(dashboard.daily, m.key, "value", m.sparkDays ?? 14)}
            sparkColor={m.color}
          />
        );
      })}
    </div>
  );
}
