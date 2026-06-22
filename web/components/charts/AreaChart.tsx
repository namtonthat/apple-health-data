"use client";

import { Area, AreaChart as RAreaChart, CartesianGrid, XAxis, YAxis } from "recharts";
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
  stack?: boolean;
  showLegend?: boolean;
  showYAxis?: boolean;
  startEndOnly?: boolean;
  curveType?: "linear" | "monotone";
  connectNulls?: boolean;
  autoMinValue?: boolean;
  minValue?: number;
  maxValue?: number;
  className?: string;
}

export function AreaChart({
  data,
  index,
  categories,
  colors,
  stack = false,
  showLegend = false,
  showYAxis = true,
  startEndOnly = false,
  curveType = "monotone",
  connectNulls = false,
  autoMinValue = false,
  minValue,
  maxValue,
  className,
}: Props) {
  const config = chartConfigFrom(categories, colors);
  const ticks =
    startEndOnly && data.length > 1
      ? [data[0][index] as string, data[data.length - 1][index] as string]
      : undefined;
  const domain: [number | string, number | string] = [
    minValue ?? (autoMinValue ? "auto" : 0),
    maxValue ?? "auto",
  ];

  return (
    <ChartContainer config={config} className={className}>
      <RAreaChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
        <CartesianGrid vertical={false} strokeOpacity={0.1} />
        <XAxis
          dataKey={index}
          tickLine={false}
          axisLine={false}
          ticks={ticks}
          tick={{ fontSize: 10 }}
          minTickGap={20}
        />
        {showYAxis && <YAxis tickLine={false} axisLine={false} width={28} tick={{ fontSize: 10 }} domain={domain} />}
        <ChartTooltip content={<ChartTooltipContent />} />
        {showLegend && <ChartLegend content={<ChartLegendContent />} />}
        {categories.map((cat, i) => (
          <Area
            key={cat}
            dataKey={cat}
            type={curveType}
            stackId={stack ? "a" : undefined}
            stroke={hex(colors[i] ?? "blue")}
            fill={hex(colors[i] ?? "blue")}
            fillOpacity={stack ? 0.5 : 0.2}
            strokeWidth={2}
            connectNulls={connectNulls}
            dot={false}
          />
        ))}
      </RAreaChart>
    </ChartContainer>
  );
}
