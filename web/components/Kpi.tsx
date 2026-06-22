import { Card } from "@/components/ui/card";
import { SparkAreaChart } from "@/components/charts/SparkAreaChart";
import type { Tone } from "@/lib/data";

interface KpiProps {
  label: string;
  value: string;
  sub?: string;
  delta?: { pct: number; above: boolean; tone: Tone } | null;
  spark?: Record<string, string | number>[];
  sparkColor?: string;
}

const TONE_CLASS: Record<Tone, string> = {
  emerald: "bg-emerald-400/10 text-emerald-400",
  amber: "bg-amber-400/10 text-amber-400",
  rose: "bg-rose-400/10 text-rose-400",
};

export function Kpi({ label, value, sub, delta, spark, sparkColor = "blue" }: KpiProps) {
  return (
    <Card className="p-3">
      <div className="flex items-start justify-between gap-2">
        <p className="text-xs text-gray-400">{label}</p>
        {delta && (
          <span
            className={`inline-flex items-center gap-0.5 rounded-full px-1.5 py-0.5 text-xs font-medium ${TONE_CLASS[delta.tone]}`}
          >
            {delta.above ? "↑" : "↓"}
            {Math.abs(delta.pct)}%
          </span>
        )}
      </div>
      <p className="mt-1 text-2xl font-semibold text-white">{value}</p>
      <div className="mt-1 flex items-end justify-between gap-2">
        {sub ? <p className="text-xs text-gray-500">{sub}</p> : <span />}
        {spark && spark.length > 1 && (
          <SparkAreaChart
            data={spark}
            categories={["value"]}
            index="date"
            colors={[sparkColor]}
            className="h-8 w-20"
          />
        )}
      </div>
    </Card>
  );
}
