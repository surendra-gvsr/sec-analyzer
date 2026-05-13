import type {
  CompareResponse,
  BenchmarkResultResponse,
  DataStatusResponse,
  PipelineStatusResponse,
  QueryResponse,
  QueryMode,
} from './types';

// Relative BASE routes through the Vercel proxy rewrite (vercel.json).
// The proxy keeps connections open — no short edge timeout observed in practice.
// Direct browser→Render is blocked by Cloudflare WAF (OPTIONS preflight fails).
const BASE = '';

// Render free tier cold start + RAG pipeline can take up to 3 min on first hit.
const QUERY_TIMEOUT_MS = 240_000;
const DEFAULT_TIMEOUT_MS = 30_000;

function withTimeout(ms: number): AbortSignal {
  return AbortSignal.timeout(ms);
}

function humanizeError(
  e: unknown,
  responseStatus?: number,
  responseText?: string
): Error {
  if (responseStatus === 503) {
    const detail = responseText?.includes('Index not built')
      ? 'Index not built yet — go to the Pipeline tab and click Build Index.'
      : 'Backend is not ready — please try again in a moment.';
    return new Error(detail);
  }
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
  let status: number | undefined;
  let text: string | undefined;
  try {
    const res = await fetch(`${BASE}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: withTimeout(timeoutMs),
    });
    if (!res.ok) {
      status = res.status;
      text = await res.text();
      throw new Error(`${status}: ${text}`);
    }
    return res.json() as Promise<T>;
  } catch (e) {
    throw humanizeError(e, status, text);
  }
}

async function get<T>(
  path: string,
  timeoutMs = DEFAULT_TIMEOUT_MS
): Promise<T> {
  let status: number | undefined;
  let text: string | undefined;
  try {
    const res = await fetch(`${BASE}${path}`, {
      cache: 'no-store',
      signal: withTimeout(timeoutMs),
    });
    if (!res.ok) {
      status = res.status;
      text = await res.text();
      throw new Error(`${status}: ${text}`);
    }
    return res.json() as Promise<T>;
  } catch (e) {
    throw humanizeError(e, status, text);
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
