'use client';

import { useEffect, useState, useCallback } from 'react';
import { api } from '@/lib/api';
import { DataStatusGrid } from '@/components/pipeline/DataStatusGrid';
import { PipelineTriggers } from '@/components/pipeline/PipelineTriggers';
import type { DataStatusResponse } from '@/lib/types';

export default function PipelinePage() {
  const [status, setStatus] = useState<DataStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const refresh = useCallback(() => {
    setLoading(true);
    api
      .dataStatus()
      .then(setStatus)
      .catch((e) =>
        setLoadError(e instanceof Error ? e.message : 'Failed to load status')
      )
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return (
    <div className="mx-auto max-w-4xl px-4 py-8 md:px-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight">Data Pipeline</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Download, parse, and index SEC 10-K filings
        </p>
      </div>
      <div className="space-y-8">
        <div>
          <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-muted-foreground">
            Pipeline Steps
          </p>
          <PipelineTriggers onStatusChange={refresh} />
        </div>
        <div>
          <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-muted-foreground">
            Data Status
          </p>
          {loading && <p className="text-sm text-muted-foreground">Loading…</p>}
          {loadError && <p className="text-sm text-destructive">{loadError}</p>}
          {status && <DataStatusGrid status={status} />}
        </div>
      </div>
    </div>
  );
}
