import { hex } from "@/lib/chart";

interface Props {
  value: number;
  radius?: number;
  strokeWidth?: number;
  color?: string;
  children?: React.ReactNode;
}

export function ProgressCircle({
  value,
  radius = 34,
  strokeWidth = 7,
  color = "blue",
  children,
}: Props) {
  const normalized = Math.max(0, Math.min(100, value));
  const r = radius - strokeWidth / 2;
  const circumference = 2 * Math.PI * r;
  const offset = circumference - (normalized / 100) * circumference;
  const size = radius * 2;

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={radius} cy={radius} r={r} fill="none" stroke="#1f2937" strokeWidth={strokeWidth} />
        <circle
          cx={radius}
          cy={radius}
          r={r}
          fill="none"
          stroke={hex(color)}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">{children}</div>
    </div>
  );
}
