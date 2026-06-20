import dashboardJson from "@/data/dashboard.json";

// ── Types (loose — every metric can be null on a given day) ────────────────
export type Num = number | null;

export interface DailyRow {
  date: string;
  sleep_hours?: Num;
  sleep_deep_hours?: Num;
  sleep_rem_hours?: Num;
  sleep_light_hours?: Num;
  hrv_ms?: Num;
  resting_hr_bpm?: Num;
  vo2_max?: Num;
  weight_kg?: Num;
  bmi?: Num;
  steps?: Num;
  protein_g?: Num;
  carbs_g?: Num;
  fat_g?: Num;
  fiber_g?: Num;
  water_ml?: Num;
  logged_calories?: Num;
  calculated_calories?: Num;
  workouts?: Num;
  total_volume_kg?: Num;
}

export interface ReadinessRow {
  date: string;
  readiness_score?: Num;
  hrv_score?: Num;
  rhr_score?: Num;
  sleep_score?: Num;
  deep_score?: Num;
}

export interface WeightRow {
  date: string;
  weight_kg?: Num;
  avg_7d?: Num;
  avg_30d?: Num;
  avg_60d?: Num;
}

export interface WorkoutRow {
  workout_date: string;
  workout_name: string;
  day_name?: string;
  workout_duration_minutes?: Num;
  unique_exercises?: Num;
  total_sets?: Num;
  working_sets?: Num;
  total_reps?: Num;
  total_volume_kg?: Num;
  max_weight_kg?: Num;
  avg_rpe?: Num;
}

export interface E1rmRow {
  workout_date: string;
  squat_e1rm?: Num;
  bench_e1rm?: Num;
  deadlift_e1rm?: Num;
  estimated_total?: Num;
}

export interface StravaRow {
  activity_date: string;
  activity_name: string;
  activity_type?: string;
  distance_km?: Num;
  moving_time_minutes?: Num;
  elevation_gain_m?: Num;
  avg_heartrate?: Num;
  avg_pace_min_per_km?: Num;
  avg_speed_kmh?: Num;
}

export interface Dashboard {
  generated_at: string;
  last_data_date: string;
  today: string;
  user_name: string;
  goals: Record<string, number>;
  latest: Record<string, Num>;
  daily: DailyRow[];
  readiness: ReadinessRow[];
  weight: WeightRow[];
  workouts: WorkoutRow[];
  e1rm: E1rmRow[];
  prs: Record<string, number | string | null>;
  macro_avg: Record<string, Num>;
  strava: StravaRow[];
}

export const dashboard = dashboardJson as unknown as Dashboard;

// ── Helpers ────────────────────────────────────────────────────────────────
export function lastN<T>(arr: T[], n: number): T[] {
  return arr.slice(Math.max(0, arr.length - n));
}

/** [{date, <name>}] for a metric, dropping null days — ready for Tremor charts. */
export function series(
  rows: { date: string }[],
  key: string,
  name: string,
  n?: number,
): Record<string, string | number>[] {
  const out = rows
    .map((r) => r as Record<string, unknown>)
    .filter((r) => r[key] !== null && r[key] !== undefined)
    .map((r) => ({ date: shortDate(r.date as string), [name]: r[key] as number }));
  return n ? lastN(out, n) : out;
}

export function shortDate(iso: string): string {
  const [, m, d] = iso.split("-");
  const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  return `${d} ${months[parseInt(m, 10) - 1]}`;
}

export function fmt(value: Num | undefined, digits = 0, unit = ""): string {
  if (value === null || value === undefined) return "-";
  const n = digits > 0 ? value.toFixed(digits) : Math.round(value).toString();
  return `${n}${unit}`;
}

export type Tone = "emerald" | "amber" | "rose";

/** Goal comparison. `pct` is signed vs goal; `above` drives the arrow; `tone` the colour.
 *  Arrow shows position vs goal; colour shows whether that's on track (direction-aware). */
export function goalStatus(
  value: Num,
  goal: number | undefined,
  dir: "higher" | "lower" | "target" = "higher",
): { pct: number; above: boolean; onTrack: boolean; tone: Tone } | null {
  if (value === null || value === undefined || !goal) return null;
  const diffPct = ((value - goal) / goal) * 100;
  const absPct = Math.abs(diffPct);
  let onTrack: boolean;
  if (dir === "higher") onTrack = value >= goal * 0.95;
  else if (dir === "lower") onTrack = value <= goal * 1.05;
  else onTrack = absPct <= 15;

  const tone: Tone = onTrack ? "emerald" : absPct <= 15 ? "amber" : "rose";
  return { pct: Math.round(diffPct), above: value >= goal, onTrack, tone };
}
