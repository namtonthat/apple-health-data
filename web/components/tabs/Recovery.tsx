import { AreaChart } from "@/components/charts/AreaChart";
import { BarChart } from "@/components/charts/BarChart";
import { LineChart } from "@/components/charts/LineChart";
import { ChartCard } from "@/components/ChartCard";
import { dashboard, lastN, shortDate } from "@/lib/data";

export function Recovery() {
  const daily = dashboard.daily;

  const sleep = lastN(daily, 21)
    .filter((r) => r.sleep_hours != null)
    .map((r) => ({
      date: shortDate(r.date),
      Deep: r.sleep_deep_hours ?? 0,
      REM: r.sleep_rem_hours ?? 0,
      Light: r.sleep_light_hours ?? 0,
    }));

  const hrv = lastN(daily, 30)
    .filter((r) => r.hrv_ms != null)
    .map((r) => ({ date: shortDate(r.date), HRV: r.hrv_ms }));

  const rhr = lastN(daily, 30)
    .filter((r) => r.resting_hr_bpm != null)
    .map((r) => ({ date: shortDate(r.date), "Resting HR": r.resting_hr_bpm }));

  const steps = lastN(daily, 14)
    .filter((r) => r.steps != null)
    .map((r) => ({ date: shortDate(r.date), Steps: r.steps }));

  const readiness = lastN(dashboard.readiness, 30)
    .filter((r) => r.readiness_score != null)
    .map((r) => ({ date: shortDate(r.date), Readiness: r.readiness_score }));

  return (
    <div className="space-y-3">
      <ChartCard title="Sleep stages" subtitle="Last 21 nights · hours">
        <AreaChart
          data={sleep}
          index="date"
          categories={["Deep", "REM", "Light"]}
          colors={["indigo", "violet", "sky"]}
          stack
          showLegend
          showYAxis={false}
          startEndOnly
          className="h-44"
        />
      </ChartCard>

      <ChartCard title="Readiness" subtitle="Last 30 days">
        <LineChart
          data={readiness}
          index="date"
          categories={["Readiness"]}
          colors={["emerald"]}
          showLegend={false}
          startEndOnly
          minValue={0}
          maxValue={100}
          className="h-40"
        />
      </ChartCard>

      <div className="grid grid-cols-1 gap-3">
        <ChartCard title="HRV" subtitle={`Goal ${dashboard.goals.hrv_ms} ms`}>
          <LineChart
            data={hrv}
            index="date"
            categories={["HRV"]}
            colors={["violet"]}
            showLegend={false}
            startEndOnly
            className="h-36"
          />
        </ChartCard>

        <ChartCard title="Resting heart rate" subtitle={`Goal ${dashboard.goals.resting_hr_bpm} bpm`}>
          <LineChart
            data={rhr}
            index="date"
            categories={["Resting HR"]}
            colors={["rose"]}
            showLegend={false}
            startEndOnly
            className="h-36"
          />
        </ChartCard>

        <ChartCard title="Steps" subtitle="Last 14 days">
          <BarChart
            data={steps}
            index="date"
            categories={["Steps"]}
            colors={["cyan"]}
            showLegend={false}
            showYAxis={false}
            startEndOnly
            className="h-36"
          />
        </ChartCard>
      </div>
    </div>
  );
}
