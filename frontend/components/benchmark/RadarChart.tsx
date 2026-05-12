'use client'

import {
  Radar, RadarChart, PolarGrid, PolarAngleAxis, Legend, ResponsiveContainer,
} from 'recharts'
import type { BenchmarkResultResponse } from '@/lib/types'

interface RadarChartCardProps {
  summary: BenchmarkResultResponse['summary']
}

export function RadarChartCard({ summary }: RadarChartCardProps) {
  const data = [
    { metric: 'TRA', structured: Math.round(summary.structured.TRA * 100), naive: Math.round(summary.naive.TRA * 100) },
    { metric: 'ACS', structured: Math.round(summary.structured.ACS * 100), naive: Math.round(summary.naive.ACS * 100) },
    { metric: 'CYC', structured: Math.round(summary.structured.CYC * 100), naive: Math.round(summary.naive.CYC * 100) },
  ]
  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <p className="mb-4 text-xs font-semibold uppercase tracking-widest text-muted-foreground">
        Structured vs Naive — Radar
      </p>
      <div className="h-44 sm:h-56">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart data={data}>
            <PolarGrid stroke="hsl(var(--border))" />
            <PolarAngleAxis dataKey="metric" tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }} />
            <Radar name="Structured" dataKey="structured" stroke="hsl(var(--chart-1))" fill="hsl(var(--chart-1))" fillOpacity={0.25} />
            <Radar name="Naive" dataKey="naive" stroke="hsl(var(--chart-3))" fill="hsl(var(--chart-3))" fillOpacity={0.15} />
            <Legend wrapperStyle={{ fontSize: 11, color: 'hsl(var(--muted-foreground))' }} />
          </RadarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
