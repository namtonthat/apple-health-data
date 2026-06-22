"use client";

import { Area, AreaChart as RAreaChart } from "recharts";
import { ChartContainer } from "@/components/ui/chart";
import { chartConfigFrom, hex } from "@/lib/chart";

interface Props {
  data: Record<string, unknown>[];
  index: string;
  categories: string[];
  colors: string[];
  className?: string;
}

export function SparkAreaChart({ data, index, categories, colors, className }: Props) {
  const config = chartConfigFrom(categories, colors);
  const color = hex(colors[0] ?? "blue");
  return (
    <ChartContainer config={config} className={className}>
      <RAreaChart data={data} margin={{ top: 1, right: 0, bottom: 1, left: 0 }}>
        <Area
          dataKey={categories[0]}
          type="monotone"
          stroke={color}
          fill={color}
          fillOpacity={0.25}
          strokeWidth={1.5}
          dot={false}
        />
      </RAreaChart>
    </ChartContainer>
  );
}
