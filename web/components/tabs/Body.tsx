import { AreaChart, BarChart, CategoryBar } from "@tremor/react";
import { ChartCard } from "@/components/ChartCard";
import { dashboard, fmt, lastN, shortDate, type Num } from "@/lib/data";

export function Body() {
  const { daily, weight, goals, latest } = dashboard;

  const weightSeries = lastN(weight, 90)
    .filter((r) => r.weight_kg != null || r.avg_7d != null)
    .map((r) => ({
      date: shortDate(r.date),
      Weight: r.weight_kg,
      "7-day avg": r.avg_7d,
      "30-day avg": r.avg_30d,
    }));

  const calories = lastN(daily, 14)
    .filter((r) => r.logged_calories != null)
    .map((r) => ({ date: shortDate(r.date), Calories: r.logged_calories }));

  const protein = lastN(daily, 21)
    .filter((r) => r.protein_g != null)
    .map((r) => ({ date: shortDate(r.date), Protein: r.protein_g }));

  // Today's macros vs goal as a share of calories
  const macros: { name: string; g: Num; goal: number; color: string }[] = [
    { name: "Protein", g: latest.protein_g, goal: goals.protein_g, color: "amber" },
    { name: "Carbs", g: latest.carbs_g, goal: goals.carbs_g, color: "sky" },
    { name: "Fat", g: latest.fat_g, goal: goals.fat_g, color: "rose" },
  ];

  return (
    <div className="space-y-3">
      <ChartCard title="Weight" subtitle={`Goal ${goals.weight_kg} kg · last 90 days`}>
        <AreaChart
          data={weightSeries}
          index="date"
          categories={["Weight", "7-day avg", "30-day avg"]}
          colors={["slate", "emerald", "amber"]}
          showLegend
          startEndOnly
          curveType="monotone"
          connectNulls
          autoMinValue
          className="h-44"
        />
      </ChartCard>

      <ChartCard title="Macros today" subtitle="Grams vs goal">
        <div className="space-y-3">
          {macros.map((m) => {
            const have = m.g ?? 0;
            const pct = Math.min(100, Math.round((have / m.goal) * 100));
            return (
              <div key={m.name}>
                <div className="mb-1 flex justify-between text-tremor-label">
                  <span className="text-gray-300">{m.name}</span>
                  <span className="text-gray-500">
                    {fmt(m.g, 0, "g")} / {fmt(m.goal, 0, "g")} · {pct}%
                  </span>
                </div>
                <CategoryBar
                  values={[pct, Math.max(0, 100 - pct)]}
                  colors={[m.color as "amber", "gray"]}
                  showLabels={false}
                  className="h-1.5"
                />
              </div>
            );
          })}
        </div>
      </ChartCard>

      <ChartCard title="Protein" subtitle={`Goal ${goals.protein_g} g · last 21 days`}>
        <BarChart
          data={protein}
          index="date"
          categories={["Protein"]}
          colors={["amber"]}
          showLegend={false}
          showYAxis={false}
          startEndOnly
          className="h-36"
        />
      </ChartCard>

      <ChartCard title="Calories logged" subtitle="Last 14 days">
        <BarChart
          data={calories}
          index="date"
          categories={["Calories"]}
          colors={["orange"]}
          showLegend={false}
          showYAxis={false}
          startEndOnly
          className="h-36"
        />
      </ChartCard>
    </div>
  );
}
