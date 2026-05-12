interface StatCardProps {
  label: string
  structured: number
  naive: number
}

function StatCard({ label, structured, naive }: StatCardProps) {
  const delta = Math.round((structured - naive) * 100)
  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">{label}</p>
      <p className="mt-2 text-4xl font-extrabold tracking-tight text-chart-2">
        {Math.round(structured * 100)}%
      </p>
      <p className="mt-1 text-xs text-muted-foreground">
        Naive: {Math.round(naive * 100)}%
        <span className={`ml-2 font-semibold ${delta >= 0 ? 'text-chart-2' : 'text-destructive'}`}>
          {delta >= 0 ? '+' : ''}{delta}pp
        </span>
      </p>
    </div>
  )
}

interface StatsGridProps {
  summary: {
    structured: { TRA: number; ACS: number; CYC: number }
    naive: { TRA: number; ACS: number; CYC: number }
  }
}

export function StatsGrid({ summary }: StatsGridProps) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
      <StatCard label="Table Retrieval (TRA)" structured={summary.structured.TRA} naive={summary.naive.TRA} />
      <StatCard label="Answer Correctness (ACS)" structured={summary.structured.ACS} naive={summary.naive.ACS} />
      <StatCard label="Cross-Year Coherence (CYC)" structured={summary.structured.CYC} naive={summary.naive.CYC} />
    </div>
  )
}
