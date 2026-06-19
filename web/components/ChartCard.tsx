import { Card } from "@tremor/react";

export function ChartCard({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  return (
    <Card className="p-4">
      <div className="mb-2">
        <p className="text-tremor-default font-medium text-white">{title}</p>
        {subtitle && <p className="text-tremor-label text-gray-500">{subtitle}</p>}
      </div>
      {children}
    </Card>
  );
}
