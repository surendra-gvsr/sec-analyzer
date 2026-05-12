export interface StructuredAnswer {
  kind: 'value' | 'trend' | 'qualitative'
  value?: number
  unit?: string
  year?: number
  ticker?: string
  metric?: string
  source?: string
  confidence: number
  series: Array<{ year: number; value: number; unit?: string }>
}

export interface QueryResponse {
  answer: string
  source_nodes: Array<{
    text: string
    score?: number
    metadata?: Record<string, unknown>
  }>
  graph_path: string[]
  latency_ms: number
  mode: string
  structured?: StructuredAnswer
}

export interface CompareResponse {
  question: string
  graph: QueryResponse
  naive: QueryResponse
}

export interface PipelineStatusResponse {
  job_id: string
  stage: string
  progress: number
  message: string
  errors: string[]
}

export interface DataStatusResponse {
  downloaded: Record<string, number[]>
  parsed: Record<string, number[]>
  index_stats: Record<string, unknown>
}

export interface BenchmarkResult {
  question_id: string
  question: string
  question_type: string
  expected: unknown
  graph_answer?: string
  naive_answer?: string
  tra_graph: boolean
  tra_naive: boolean
  acs_graph?: number
  acs_naive?: number
  cyc_graph?: boolean
  cyc_naive?: boolean
  confidence?: number
}

export interface BenchmarkResultResponse {
  generated_at: string
  total_questions: number
  summary: {
    structured: { TRA: number; ACS: number; CYC: number }
    naive: { TRA: number; ACS: number; CYC: number }
  }
  results: BenchmarkResult[]
}

export interface HealthResponse {
  status: string
  environment: string
  index_ready: boolean
  graph_nodes: number
  graph_edges: number
}

export type QueryMode = 'graph' | 'naive'
