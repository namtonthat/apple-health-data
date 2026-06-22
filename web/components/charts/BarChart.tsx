"use client";

import { Bar, BarChart as RBarChart, CartesianGrid, XAxis, YAxis } from "recharts";
import {
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart";
import { chartConfigFrom, hex } from "@/lib/chart";

interface Props {
  data: Record<string, unknown>[];
  index: string;
  categories: string[];
  colors: string[];
  showLegend?: boolean;
  showYAxis?: boolean;
  startEndOnly?: boolean;
  className?: string;
}

export function BarChart({
  data,
  index,
  categories,
  colors,
  showLegend = false,
  showYAxis = true,
  startEndOnly = false,
  className,
}: Props) {
  const config = chartConfigFrom(categories, colors);
  const ticks =
    startEndOnly && data.length > 1
      ? [data[0][index] as string, data[data.length - 1][index] as string]
      : undefined;

  return (
    <ChartContainer config={config} className={className}>
      <RBarChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
        <CartesianGrid vertical={false} strokeOpacity={0.1} />
        <XAxis
          dataKey={index}
          tickLine={false}
          axisLine={false}
          ticks={ticks}
          tick={{ fontSize: 10 }}
          minTickGap={20}
        />
        {showYAxis && <YAxis tickLine={false} axisLine={false} width={28} tick={{ fontSize: 10 }} />}
        <ChartTooltip content={<ChartTooltipContent />} />
        {showLegend && <ChartLegend content={<ChartLegendContent />} />}
        {categories.map((cat, i) => (
          <Bar key={cat} dataKey={cat} fill={hex(colors[i] ?? "blue")} radius={2} />
        ))}
      </RBarChart>
    </ChartContainer>
  );
}
