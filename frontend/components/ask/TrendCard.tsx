'use client';

import { useState } from 'react';
import {
  LineChart,
  BarChart,
  Line,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { Button } from '@/components/ui/button';
import type { StructuredAnswer } from '@/lib/types';

interface TrendCardProps {
  structured: StructuredAnswer;
}

export function TrendCard({ structured }: TrendCardProps) {
  const [chartType, setChartType] = useState<'line' | 'bar'>('line');
  if (!structured.series.length) return null;

  const data = structured.series.map((d) => ({
    year: String(d.year),
    value: d.value,
  }));

  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <div className="mb-4 flex items-center justify-between">
        <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
          Trend — {structured.metric ?? 'Value'}{' '}
          {structured.unit ? `(${structured.unit})` : ''}
        </p>
        <div className="flex gap-1">
          {(['line', 'bar'] as const).map((t) => (
            <Button
              key={t}
              variant={chartType === t ? 'default' : 'ghost'}
              size="sm"
              className="h-7 px-3 text-xs"
              onClick={() => setChartType(t)}
            >
              {t === 'line' ? 'Line' : 'Bar'}
            </Button>
          ))}
        </div>
      </div>
      <div className="h-44 sm:h-56">
        <ResponsiveContainer width="100%" height="100%">
          {chartType === 'line' ? (
            <LineChart data={data}>
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="hsl(var(--border))"
              />
              <XAxis
                dataKey="year"
                tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }}
              />
              <YAxis
                tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }}
                width={60}
              />
              <Tooltip
                contentStyle={{
                  background: 'hsl(var(--popover))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '8px',
                  color: 'hsl(var(--foreground))',
                }}
              />
              <Line
                type="monotone"
                dataKey="value"
                stroke="hsl(var(--chart-1))"
                strokeWidth={2}
                dot={{ r: 4, fill: 'hsl(var(--chart-1))' } as object}
              />
            </LineChart>
          ) : (
            <BarChart data={data}>
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="hsl(var(--border))"
              />
              <XAxis
                dataKey="year"
                tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }}
              />
              <YAxis
                tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }}
                width={60}
              />
              <Tooltip
                contentStyle={{
                  background: 'hsl(var(--popover))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '8px',
                  color: 'hsl(var(--foreground))',
                }}
              />
              <Bar
                dataKey="value"
                fill="hsl(var(--chart-1))"
                radius={[4, 4, 0, 0]}
              />
            </BarChart>
          )}
        </ResponsiveContainer>
      </div>
      <div className="mt-3 flex gap-2 overflow-x-auto pb-1">
        {structured.series.map((d) => (
          <div
            key={d.year}
            className="shrink-0 rounded-lg border border-border bg-muted/50 px-3 py-2 text-center"
          >
            <p className="text-[10px] text-muted-foreground">{d.year}</p>
            <p className="text-sm font-bold">{d.value.toLocaleString()}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
