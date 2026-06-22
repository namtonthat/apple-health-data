import type { ChartConfig } from "@/components/ui/chart";

// Tremor used Tailwind-500 hexes for chart series. Keep the same values for parity.
export const CHART_COLORS: Record<string, string> = {
  slate: "#64748b",
  gray: "#6b7280",
  red: "#ef4444",
  orange: "#f97316",
  amber: "#f59e0b",
  emerald: "#10b981",
  cyan: "#06b6d4",
  sky: "#0ea5e9",
  blue: "#3b82f6",
  indigo: "#6366f1",
  violet: "#8b5cf6",
  rose: "#f43f5e",
};

export function hex(name: string): string {
  return CHART_COLORS[name] ?? name;
}

export function chartConfigFrom(categories: string[], colors: string[]): ChartConfig {
  const config: ChartConfig = {};
  categories.forEach((cat, i) => {
    config[cat] = { label: cat, color: hex(colors[i] ?? "blue") };
  });
  return config;
}
