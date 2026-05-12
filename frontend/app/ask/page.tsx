'use client';

import { useState } from 'react';
import { api } from '@/lib/api';
import { QueryInput } from '@/components/ask/QueryInput';
import { ExampleCards } from '@/components/ask/ExampleCards';
import { AnswerCard } from '@/components/ask/AnswerCard';
import { EvidenceAccordion } from '@/components/ask/EvidenceAccordion';
import { LoadingStages } from '@/components/ask/LoadingStages';
import { QueryHistory } from '@/components/ask/QueryHistory';
import { TrendCard } from '@/components/ask/TrendCard';
import { useQueryHistory } from '@/hooks/useQueryHistory';
import type { QueryMode, QueryResponse, CompareResponse } from '@/lib/types';

export default function AskPage() {
  const [question, setQuestion] = useState('');
  const [mode, setMode] = useState<QueryMode | 'compare'>('graph');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [compare, setCompare] = useState<CompareResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitCount, setSubmitCount] = useState(0);

  const { history, push, clear } = useQueryHistory();

  const handleSubmit = async () => {
    if (!question.trim()) return;
    setSubmitCount((c) => c + 1);
    setLoading(true);
    setError(null);
    setResult(null);
    setCompare(null);
    try {
      if (mode === 'compare') {
        const data = await api.compare(question);
        setCompare(data);
        push(question, mode, data.graph);
      } else {
        const data = await api.query(question, mode);
        setResult(data);
        push(question, mode, data);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-4xl px-4 py-8 md:px-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight">Ask FilingsIQ</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Ask questions about Apple and Microsoft 10-K filings (2021–2024)
        </p>
      </div>
      <div className="space-y-5">
        <QueryInput
          value={question}
          onChange={setQuestion}
          mode={mode}
          onModeChange={setMode}
          onSubmit={handleSubmit}
          loading={loading}
        />
        <LoadingStages key={submitCount} active={loading} />
        {error && (
          <div className="rounded-lg border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            {error}
          </div>
        )}
        {result && (
          <>
            <AnswerCard result={result} />
            {result.structured?.kind === 'trend' &&
              result.structured.series.length > 0 && (
                <TrendCard structured={result.structured} />
              )}
            <EvidenceAccordion nodes={result.source_nodes} />
          </>
        )}
        {compare && (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Smart Mode
              </p>
              <AnswerCard result={compare.graph} />
            </div>
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Basic Mode
              </p>
              <AnswerCard result={compare.naive} />
            </div>
          </div>
        )}
        <QueryHistory
          history={history}
          onSelect={setQuestion}
          onClear={clear}
        />
        {!result && !compare && !loading && (
          <div>
            <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-muted-foreground">
              Example Questions
            </p>
            <ExampleCards onSelect={(q) => setQuestion(q)} />
          </div>
        )}
      </div>
    </div>
  );
}
