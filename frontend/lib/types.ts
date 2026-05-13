export interface StructuredAnswer {
  kind: 'value' | 'trend' | 'qualitative';
  value?: number;
  unit?: string;
  year?: number;
  ticker?: string;
  metric?: string;
  source?: string;
  confidence: number;
  series: Array<{ year: number; value: number; unit?: string }>;
}

export interface QueryResponse {
  answer: string;
  source_nodes: Array<{
    text: string;
    score?: number;
    metadata?: Record<string, unknown>;
  }>;
  graph_path: string[];
  latency_ms: number;
  mode: string;
  structured?: StructuredAnswer;
}

export interface CompareResponse {
  question: string;
  graph: QueryResponse;
  naive: QueryResponse;
}

export interface PipelineStatusResponse {
  job_id: string;
  stage: string;
  progress: number;
  message: string;
  errors: string[];
}

export interface DataStatusResponse {
  downloaded: Record<string, number[]>;
  parsed: Record<string, number[]>;
  index_stats: Record<string, unknown>;
}

export interface BenchmarkRunMetrics {
  answer: string;
  tra: number;          // 0 or 1
  acs: number | null;
  cyc: number | null;
  latency_ms: number;
  retrieved_chunks: number;
  table_in_context: boolean;
}

export interface BenchmarkResult {
  question_id: string;
  question: string;
  type: string;
  ticker: string;
  years: number[];
  expected_value: string | null;
  naive: BenchmarkRunMetrics;
  structured: BenchmarkRunMetrics;
}

export interface BenchmarkSummary {
  naive_tra: number;
  structured_tra: number;
  naive_acs: number;
  structured_acs: number;
  naive_cyc: number;
  structured_cyc: number;
  naive_avg_latency_ms: number;
  structured_avg_latency_ms: number;
  improvement_tra_pct: number;
  improvement_acs_pct: number;
  improvement_cyc_pct: number;
  total_questions: number;
}

export interface BenchmarkResultResponse {
  generated_at: string;
  total_questions: number;
  summary: BenchmarkSummary;
  results: BenchmarkResult[];
}

export interface HealthResponse {
  status: string;
  environment: string;
  index_ready: boolean;
  graph_nodes: number;
  graph_edges: number;
}

export type QueryMode = 'graph' | 'naive';
