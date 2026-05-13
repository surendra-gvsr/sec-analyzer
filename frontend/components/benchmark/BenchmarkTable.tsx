import { Badge } from '@/components/ui/badge';
import type { BenchmarkResult } from '@/lib/types';

interface BenchmarkTableProps {
  results: BenchmarkResult[];
}

export function BenchmarkTable({ results }: BenchmarkTableProps) {
  return (
    <div className="rounded-xl border border-border bg-card overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[640px] text-xs">
          <thead>
            <tr className="border-b border-border bg-muted/50">
              <th className="px-4 py-3 text-left font-semibold uppercase tracking-wider text-muted-foreground">
                #
              </th>
              <th className="px-4 py-3 text-left font-semibold uppercase tracking-wider text-muted-foreground">
                Question
              </th>
              <th className="px-4 py-3 text-left font-semibold uppercase tracking-wider text-muted-foreground">
                Type
              </th>
              <th className="px-4 py-3 text-center font-semibold uppercase tracking-wider text-muted-foreground">
                TRA
              </th>
              <th className="px-4 py-3 text-center font-semibold uppercase tracking-wider text-muted-foreground">
                ACS
              </th>
              <th className="px-4 py-3 text-center font-semibold uppercase tracking-wider text-muted-foreground">
                CYC
              </th>
            </tr>
          </thead>
          <tbody>
            {results.map((r, i) => {
              const s = r.structured;
              const traOk = s.tra === 1;
              const cycOk = s.cyc == null ? null : s.cyc === 1;
              return (
                <tr
                  key={r.question_id}
                  className="border-b border-border last:border-0 hover:bg-muted/30 transition-colors"
                >
                  <td className="px-4 py-3 text-muted-foreground">{i + 1}</td>
                  <td className="px-4 py-3 max-w-xs">
                    <p className="text-foreground">{r.question}</p>
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant="outline" className="text-[10px]">
                      {r.type}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span
                      className={traOk ? 'font-bold text-chart-2' : 'text-destructive'}
                    >
                      {traOk ? '✓' : '✗'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center text-muted-foreground">
                    {s.acs != null ? `${Math.round(s.acs * 100)}%` : '—'}
                  </td>
                  <td className="px-4 py-3 text-center">
                    {cycOk == null ? (
                      '—'
                    ) : (
                      <span
                        className={cycOk ? 'font-bold text-chart-2' : 'text-destructive'}
                      >
                        {cycOk ? '✓' : '✗'}
                      </span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
