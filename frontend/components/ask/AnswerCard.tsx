import { Badge } from '@/components/ui/badge';
import type { QueryResponse } from '@/lib/types';

interface AnswerCardProps {
  result: QueryResponse;
}

export function AnswerCard({ result }: AnswerCardProps) {
  const s = result.structured;

  return (
    <div className="rounded-xl border border-border bg-gradient-to-br from-chart-1/5 to-chart-2/5 p-6 shadow-md">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Badge variant={result.mode === 'graph' ? 'default' : 'secondary'}>
            {result.mode === 'graph' ? 'Smart Mode' : 'Basic Mode'}
          </Badge>
          {s?.metric && (
            <Badge variant="outline" className="text-xs">
              {s.metric}
            </Badge>
          )}
        </div>
        {s && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span>Confidence</span>
            <div className="h-1.5 w-20 overflow-hidden rounded-full bg-muted">
              <div
                className="h-full bg-chart-2 transition-all"
                style={{ width: `${Math.round(s.confidence * 100)}%` }}
              />
            </div>
            <span className="font-medium">
              {Math.round(s.confidence * 100)}%
            </span>
          </div>
        )}
      </div>

      {s && (s.ticker || s.year) && (
        <div className="mb-3 flex flex-wrap gap-3 text-xs text-muted-foreground">
          {s.ticker && (
            <span>
              Ticker: <strong className="text-foreground">{s.ticker}</strong>
            </span>
          )}
          {s.year && (
            <span>
              Year: <strong className="text-foreground">{s.year}</strong>
            </span>
          )}
          {s.source && (
            <span>
              Source: <strong className="text-foreground">{s.source}</strong>
            </span>
          )}
        </div>
      )}

      {s?.kind === 'value' && s.value != null ? (
        <div className="my-2">
          <span className="text-5xl font-extrabold tracking-tight">
            {s.value.toLocaleString()}
          </span>
          {s.unit && (
            <span className="ml-2 text-2xl font-semibold text-muted-foreground">
              {s.unit}
            </span>
          )}
        </div>
      ) : (
        <p className="text-base leading-relaxed">{result.answer}</p>
      )}

      {s?.kind === 'value' && s.value != null && result.answer && (
        <p className="mt-4 border-t border-dashed border-border pt-4 text-sm text-muted-foreground">
          {result.answer}
        </p>
      )}

      <p className="mt-3 text-xs text-muted-foreground">
        {result.latency_ms.toFixed(0)}ms · {result.source_nodes.length} chunks
        retrieved
      </p>
    </div>
  );
}
