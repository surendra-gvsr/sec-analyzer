'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { api } from '@/lib/api';
import type { PipelineStatusResponse } from '@/lib/types';

interface TriggerButtonProps {
  label: string;
  action: () => Promise<PipelineStatusResponse>;
  onDone: () => void;
}

function TriggerButton({ label, action, onDone }: TriggerButtonProps) {
  const [status, setStatus] = useState<PipelineStatusResponse | null>(null);
  const [loading, setLoading] = useState(false);

  const run = async () => {
    setLoading(true);
    try {
      const res = await action();
      setStatus(res);
      let current = res;
      const MAX_POLLS = 150;
      let polls = 0;
      while (
        current.progress < 100 &&
        current.stage !== 'error' &&
        polls < MAX_POLLS
      ) {
        await new Promise((r) => setTimeout(r, 2000));
        current = await api.pollStatus(current.job_id);
        setStatus(current);
        polls++;
      }
      if (polls >= MAX_POLLS) {
        setStatus({
          job_id: current.job_id,
          stage: 'error',
          progress: current.progress,
          message: 'Timed out waiting for job to complete',
          errors: ['Timeout after 5 minutes'],
        });
        return;
      }
      onDone();
    } catch (e) {
      setStatus({
        job_id: '',
        stage: 'error',
        progress: 0,
        message: String(e),
        errors: [],
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <div className="flex items-center justify-between mb-3">
        <p className="text-sm font-semibold">{label}</p>
        <Button
          onClick={run}
          disabled={loading}
          size="sm"
          variant="outline"
          className="min-h-11 hover:bg-muted"
        >
          {loading ? 'Running…' : 'Run'}
        </Button>
      </div>
      {status && (
        <>
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
            <div
              className="h-full bg-chart-1 transition-all duration-300"
              style={{ width: `${status.progress}%` }}
            />
          </div>
          <p className="mt-2 text-xs text-muted-foreground">{status.message}</p>
          {status.errors.length > 0 && (
            <p className="mt-1 text-xs text-destructive">
              {status.errors.join(', ')}
            </p>
          )}
        </>
      )}
    </div>
  );
}

interface PipelineTriggersProps {
  onStatusChange: () => void;
}

export function PipelineTriggers({ onStatusChange }: PipelineTriggersProps) {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
      <TriggerButton
        label="1. Download Filings"
        action={() => api.download()}
        onDone={onStatusChange}
      />
      <TriggerButton
        label="2. Parse with LlamaParse"
        action={() => api.parse()}
        onDone={onStatusChange}
      />
      <TriggerButton
        label="3. Build Index"
        action={() => api.buildIndex()}
        onDone={onStatusChange}
      />
      <TriggerButton
        label="4. Run Benchmark"
        action={() => api.runBenchmark()}
        onDone={onStatusChange}
      />
    </div>
  );
}
