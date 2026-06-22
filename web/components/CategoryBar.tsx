import { hex } from "@/lib/chart";

interface Props {
  values: number[];
  colors: string[];
  showLabels?: boolean;
  className?: string;
}

export function CategoryBar({ values, colors, showLabels = false, className = "" }: Props) {
  const total = values.reduce((a, b) => a + b, 0) || 1;
  return (
    <div className={`flex w-full overflow-hidden rounded-full ${className}`}>
      {values.map((v, i) => (
        <div
          key={i}
          style={{ width: `${(v / total) * 100}%`, backgroundColor: hex(colors[i] ?? "gray") }}
          className="h-full"
        >
          {showLabels && v > 0 ? <span className="sr-only">{v}</span> : null}
        </div>
      ))}
    </div>
  );
}
