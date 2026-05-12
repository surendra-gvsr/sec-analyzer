import { cn } from '@/lib/utils';
import type { DataStatusResponse } from '@/lib/types';

interface DataStatusGridProps {
  status: DataStatusResponse;
}

const ALL_YEARS = [2021, 2022, 2023, 2024];

export function DataStatusGrid({ status }: DataStatusGridProps) {
  const tickers = Object.keys(status.downloaded);
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
      {tickers.map((ticker) => (
        <div
          key={ticker}
          className="rounded-xl border border-border bg-card p-4"
        >
          <p className="mb-3 text-base font-bold">{ticker}</p>
          <div className="flex flex-wrap gap-3">
            {ALL_YEARS.map((yr) => {
              const downloaded = status.downloaded[ticker]?.includes(yr);
              const parsed = status.parsed[ticker]?.includes(yr);
              return (
                <div
                  key={yr}
                  className="flex items-center gap-1.5 text-xs text-muted-foreground"
                >
                  <span
                    className={cn(
                      'h-2 w-2 rounded-full',
                      parsed
                        ? 'bg-chart-2'
                        : downloaded
                          ? 'bg-chart-3'
                          : 'bg-muted-foreground/30'
                    )}
                  />
                  {yr}
                </div>
              );
            })}
          </div>
          <div className="mt-2 flex gap-3 text-[10px] text-muted-foreground">
            <span className="flex items-center gap-1">
              <span className="h-1.5 w-1.5 rounded-full bg-chart-2 inline-block" />{' '}
              Parsed
            </span>
            <span className="flex items-center gap-1">
              <span className="h-1.5 w-1.5 rounded-full bg-chart-3 inline-block" />{' '}
              Downloaded
            </span>
            <span className="flex items-center gap-1">
              <span className="h-1.5 w-1.5 rounded-full bg-muted-foreground/30 inline-block" />{' '}
              Missing
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}
