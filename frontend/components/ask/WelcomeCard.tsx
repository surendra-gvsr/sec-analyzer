'use client';

import { useEffect, useState } from 'react';
import { X, Database, MessageSquare, BarChart3 } from 'lucide-react';

const DISMISS_KEY = 'filingsiq:welcome-dismissed:v1';

export function WelcomeCard() {
  const [dismissed, setDismissed] = useState(true);

  useEffect(() => {
    setDismissed(typeof window !== 'undefined' && localStorage.getItem(DISMISS_KEY) === '1');
  }, []);

  if (dismissed) return null;

  const handleDismiss = () => {
    try {
      localStorage.setItem(DISMISS_KEY, '1');
    } catch {}
    setDismissed(true);
  };

  return (
    <div className="relative rounded-xl border border-border bg-card px-5 py-5 sm:px-6">
      <button
        type="button"
        onClick={handleDismiss}
        aria-label="Dismiss welcome"
        className="absolute right-3 top-3 rounded-md p-1 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
      >
        <X className="h-4 w-4" />
      </button>

      <h2 className="text-lg font-semibold tracking-tight">
        Welcome to FilingsIQ
      </h2>
      <p className="mt-1 text-sm text-muted-foreground">
        Ask plain-English questions about real SEC 10-K filings — answers come back grounded in the exact passages used.
      </p>

      <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
        <div className="flex gap-3">
          <Database className="h-4 w-4 mt-0.5 shrink-0 text-chart-2" />
          <div>
            <p className="text-xs font-semibold text-foreground">Data</p>
            <p className="text-xs text-muted-foreground">
              Apple &amp; Microsoft 10-K filings, FY 2021–2024.
            </p>
          </div>
        </div>
        <div className="flex gap-3">
          <MessageSquare className="h-4 w-4 mt-0.5 shrink-0 text-chart-2" />
          <div>
            <p className="text-xs font-semibold text-foreground">How to use</p>
            <p className="text-xs text-muted-foreground">
              Type a question. Pick <span className="font-medium text-foreground">Smart</span> (structure-aware), <span className="font-medium text-foreground">Basic</span> (vector baseline), or <span className="font-medium text-foreground">Compare</span> (both side-by-side).
            </p>
          </div>
        </div>
        <div className="flex gap-3">
          <BarChart3 className="h-4 w-4 mt-0.5 shrink-0 text-chart-2" />
          <div>
            <p className="text-xs font-semibold text-foreground">Why it matters</p>
            <p className="text-xs text-muted-foreground">
              Structure-aware retrieval beats naive RAG on financial tables. See the <a href="/benchmark" className="underline hover:text-foreground">Benchmark</a> page.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
