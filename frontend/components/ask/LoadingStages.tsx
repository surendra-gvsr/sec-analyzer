'use client';

import { useEffect, useState } from 'react';
import { Check, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

const STAGES = [
  { id: 'retrieve', label: 'Retrieving relevant chunks' },
  { id: 'rerank', label: 'Reranking with flashrank' },
  { id: 'synthesize', label: 'Synthesizing answer' },
];

interface LoadingStagesProps {
  active: boolean;
}

export function LoadingStages({ active }: LoadingStagesProps) {
  const [current, setCurrent] = useState(0);

  useEffect(() => {
    if (!active) {
      setCurrent(0);
      return;
    }
    const timings = [800, 1600, 2800];
    const timers = timings.map((t, i) =>
      setTimeout(() => setCurrent(i + 1), t)
    );
    return () => timers.forEach(clearTimeout);
  }, [active]);

  if (!active) return null;

  return (
    <div className="rounded-xl border border-border bg-card px-6 py-5 space-y-3">
      {STAGES.map((stage, i) => (
        <div
          key={stage.id}
          className={cn(
            'flex items-center gap-3 text-sm transition-colors',
            i < current && 'text-chart-2',
            i === current && 'text-foreground',
            i > current && 'text-muted-foreground/40'
          )}
        >
          <div className="w-5 flex justify-center shrink-0">
            {i < current ? (
              <Check className="h-4 w-4" />
            ) : i === current ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <div className="h-2 w-2 rounded-full bg-current" />
            )}
          </div>
          {stage.label}
        </div>
      ))}
    </div>
  );
}
