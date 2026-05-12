'use client'

import { useEffect, useState } from 'react'
import { api } from '@/lib/api'
import { StatsGrid } from '@/components/benchmark/StatsGrid'
import { RadarChartCard } from '@/components/benchmark/RadarChart'
import { BenchmarkTable } from '@/components/benchmark/BenchmarkTable'
import { Button } from '@/components/ui/button'
import type { BenchmarkResultResponse } from '@/lib/types'

export default function BenchmarkPage() {
  const [data, setData] = useState<BenchmarkResultResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)
  const [runError, setRunError] = useState<string | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)

  useEffect(() => {
    api.benchmarkResults()
      .then(setData)
      .catch(e => setLoadError(e instanceof Error ? e.message : 'Failed to load results'))
      .finally(() => setLoading(false))
  }, [])

  const handleRun = async () => {
    setRunning(true)
    setRunError(null)
    try {
      const job = await api.runBenchmark()
      let current = job
      const MAX_POLLS = 150
      let polls = 0
      while (current.progress < 100 && current.stage !== 'error' && polls < MAX_POLLS) {
        await new Promise(r => setTimeout(r, 2000))
        current = await api.pollStatus(current.job_id)
        polls++
      }
      if (current.stage === 'error') {
        setRunError(current.errors[0] ?? 'Benchmark failed')
        return
      }
      const fresh = await api.benchmarkResults()
      setData(fresh)
    } catch (e) {
      setRunError(e instanceof Error ? e.message : 'Benchmark failed')
    } finally {
      setRunning(false)
    }
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 md:px-8">
      <div className="mb-8 flex items-end justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Benchmark Results</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Structured GraphRAG vs naive vector retrieval across 10 questions
          </p>
        </div>
        <div>
          <Button onClick={handleRun} disabled={running} size="sm" variant="outline">
            {running ? 'Running…' : 'Re-run Benchmark'}
          </Button>
          {runError && (
            <p className="mt-2 text-xs text-destructive">{runError}</p>
          )}
        </div>
      </div>
      {loading && <p className="text-sm text-muted-foreground">Loading results…</p>}
      {loadError && <p className="text-sm text-destructive">{loadError}</p>}
      {data && (
        <div className="space-y-6">
          <StatsGrid summary={data.summary} />
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <RadarChartCard summary={data.summary} />
            <div className="rounded-xl border border-border bg-card p-5">
              <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-muted-foreground">Metrics</p>
              <div className="space-y-3 text-sm text-muted-foreground">
                <p><strong className="text-foreground">TRA</strong> — Table Retrieval Accuracy: did retrieved chunks contain the expected Markdown table row?</p>
                <p><strong className="text-foreground">ACS</strong> — Answer Correctness Score: numeric answer within 5% of expected?</p>
                <p><strong className="text-foreground">CYC</strong> — Cross-Year Coherence: does the answer mention all required years?</p>
              </div>
              <p className="mt-4 text-xs text-muted-foreground">
                Generated: {data.generated_at} · {data.total_questions} questions
              </p>
            </div>
          </div>
          <BenchmarkTable results={data.results} />
        </div>
      )}
    </div>
  )
}
