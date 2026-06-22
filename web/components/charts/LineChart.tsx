"use client";

import { CartesianGrid, Line, LineChart as RLineChart, XAxis, YAxis } from "recharts";
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
  startEndOnly?: boolean;
  minValue?: number;
  maxValue?: number;
  className?: string;
}

export function LineChart({
  data,
  index,
  categories,
  colors,
  showLegend = false,
  startEndOnly = false,
  minValue,
  maxValue,
  className,
}: Props) {
  const config = chartConfigFrom(categories, colors);
  const ticks =
    startEndOnly && data.length > 1
      ? [data[0][index] as string, data[data.length - 1][index] as string]
      : undefined;
  const domain: [number | string, number | string] = [minValue ?? "auto", maxValue ?? "auto"];

  return (
    <ChartContainer config={config} className={className}>
      <RLineChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
        <CartesianGrid vertical={false} strokeOpacity={0.1} />
        <XAxis
          dataKey={index}
          tickLine={false}
          axisLine={false}
          ticks={ticks}
          tick={{ fontSize: 10 }}
          minTickGap={20}
        />
        <YAxis tickLine={false} axisLine={false} width={28} tick={{ fontSize: 10 }} domain={domain} />
        <ChartTooltip content={<ChartTooltipContent />} />
        {showLegend && <ChartLegend content={<ChartLegendContent />} />}
        {categories.map((cat, i) => (
          <Line
            key={cat}
            dataKey={cat}
            type="monotone"
            stroke={hex(colors[i] ?? "blue")}
            strokeWidth={2}
            dot={false}
          />
        ))}
      </RLineChart>
    </ChartContainer>
  );
}
