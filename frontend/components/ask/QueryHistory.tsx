'use client'

import { Clock, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import type { HistoryEntry } from '@/hooks/useQueryHistory'

interface QueryHistoryProps {
  history: HistoryEntry[]
  onSelect: (q: string) => void
  onClear: () => void
}

export function QueryHistory({ history, onSelect, onClear }: QueryHistoryProps) {
  if (!history.length) return null
  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-muted-foreground">
          <Clock className="h-3.5 w-3.5" />
          Recent Queries
        </div>
        <Button variant="ghost" size="icon" className="h-6 w-6 hover:text-destructive" onClick={onClear} aria-label="Clear history">
          <Trash2 className="h-3.5 w-3.5" />
        </Button>
      </div>
      <ScrollArea className="max-h-48">
        <div className="space-y-1">
          {history.map(entry => (
            <button
              key={entry.id}
              onClick={() => onSelect(entry.question)}
              className="w-full rounded-lg px-3 py-2.5 text-left text-xs transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <p className="font-medium text-foreground line-clamp-1">{entry.question}</p>
              <p className="mt-0.5 text-muted-foreground line-clamp-1">{entry.answer}</p>
            </button>
          ))}
        </div>
      </ScrollArea>
    </div>
  )
}
