import type {
  CompareResponse,
  BenchmarkResultResponse,
  DataStatusResponse,
  PipelineStatusResponse,
  QueryResponse,
  QueryMode,
} from './types'

const BASE = process.env.NEXT_PUBLIC_API_URL ?? ''

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`${res.status}: ${text}`)
  }
  return res.json() as Promise<T>
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { cache: 'no-store' })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`${res.status}: ${text}`)
  }
  return res.json() as Promise<T>
}

export const api = {
  query: (question: string, mode: QueryMode) =>
    post<QueryResponse>('/api/query', { question, mode }),

  compare: (question: string) =>
    post<CompareResponse>('/api/query/compare', { question, mode: 'graph' }),

  benchmarkResults: () =>
    get<BenchmarkResultResponse>('/api/benchmark/results'),

  runBenchmark: () =>
    post<PipelineStatusResponse>('/api/benchmark/run', {}),

  dataStatus: () =>
    get<DataStatusResponse>('/api/pipeline/data-status'),

  download: (tickers?: string[], years?: number[]) =>
    post<PipelineStatusResponse>('/api/pipeline/download', { tickers, years }),

  parse: (tickers?: string[], years?: number[]) =>
    post<PipelineStatusResponse>('/api/pipeline/parse', { tickers, years }),

  buildIndex: (tickers?: string[], years?: number[]) =>
    post<PipelineStatusResponse>('/api/pipeline/build-index', { tickers, years }),

  pollStatus: (jobId: string) =>
    get<PipelineStatusResponse>(`/api/pipeline/status/${jobId}`),
}
