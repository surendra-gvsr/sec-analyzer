import type {
  CompareResponse,
  BenchmarkResultResponse,
  DataStatusResponse,
  PipelineStatusResponse,
  QueryResponse,
  QueryMode,
} from './types';

const BASE = process.env.NEXT_PUBLIC_API_URL ?? '';

// Query endpoint can take up to 90s (cold start + RAG pipeline).
// Status/data endpoints should respond quickly once the service is up.
const QUERY_TIMEOUT_MS = 120_000;
const DEFAULT_TIMEOUT_MS = 30_000;

function withTimeout(ms: number): AbortSignal {
  return AbortSignal.timeout(ms);
}

function humanizeError(e: unknown): Error {
  if (e instanceof DOMException && e.name === 'TimeoutError') {
    return new Error('Backend is starting up — please try again in a moment.');
  }
  if (e instanceof TypeError && e.message.includes('fetch')) {
    return new Error('Cannot reach the backend — check your connection.');
  }
  return e instanceof Error ? e : new Error('Unknown error');
}

async function post<T>(
  path: string,
  body: unknown,
  timeoutMs = DEFAULT_TIMEOUT_MS
): Promise<T> {
  try {
    const res = await fetch(`${BASE}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: withTimeout(timeoutMs),
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(`${res.status}: ${text}`);
    }
    return res.json() as Promise<T>;
  } catch (e) {
    throw humanizeError(e);
  }
}

async function get<T>(
  path: string,
  timeoutMs = DEFAULT_TIMEOUT_MS
): Promise<T> {
  try {
    const res = await fetch(`${BASE}${path}`, {
      cache: 'no-store',
      signal: withTimeout(timeoutMs),
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(`${res.status}: ${text}`);
    }
    return res.json() as Promise<T>;
  } catch (e) {
    throw humanizeError(e);
  }
}

export const api = {
  query: (question: string, mode: QueryMode) =>
    post<QueryResponse>('/api/query', { question, mode }, QUERY_TIMEOUT_MS),

  compare: (question: string) =>
    post<CompareResponse>(
      '/api/query/compare',
      { question, mode: 'graph' },
      QUERY_TIMEOUT_MS
    ),

  benchmarkResults: () =>
    get<BenchmarkResultResponse>('/api/benchmark/results'),

  runBenchmark: () => post<PipelineStatusResponse>('/api/benchmark/run', {}),

  dataStatus: () => get<DataStatusResponse>('/api/pipeline/data-status'),

  download: (tickers?: string[], years?: number[]) =>
    post<PipelineStatusResponse>('/api/pipeline/download', { tickers, years }),

  parse: (tickers?: string[], years?: number[]) =>
    post<PipelineStatusResponse>('/api/pipeline/parse', { tickers, years }),

  buildIndex: (tickers?: string[], years?: number[]) =>
    post<PipelineStatusResponse>('/api/pipeline/build-index', {
      tickers,
      years,
    }),

  pollStatus: (jobId: string) =>
    get<PipelineStatusResponse>(`/api/pipeline/status/${jobId}`),
};
