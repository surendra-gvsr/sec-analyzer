'use client'

import { ChevronRight } from 'lucide-react'
import type { QueryResponse } from '@/lib/types'

interface EvidenceAccordionProps {
  nodes: QueryResponse['source_nodes']
}

export function EvidenceAccordion({ nodes }: EvidenceAccordionProps) {
  if (!nodes.length) return null
  return (
    <details className="group rounded-xl border border-border bg-card overflow-hidden">
      <summary className="flex cursor-pointer select-none list-none items-center gap-2 px-5 py-3.5 text-xs font-semibold text-muted-foreground hover:text-foreground transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
        <ChevronRight className="h-3.5 w-3.5 transition-transform group-open:rotate-90" />
        Evidence — {nodes.length} chunks retrieved
      </summary>
      <div className="flex flex-col gap-2 px-5 pb-5">
        {nodes.map((node, i) => {
          const meta = node.metadata as Record<string, string> | undefined
          return (
            <div key={i} className="rounded-lg border border-border bg-muted/50 p-3">
              {meta && (
                <div className="mb-1.5 flex gap-3 text-[10px] text-muted-foreground">
                  {meta['company'] && <span>Company: <strong>{meta['company']}</strong></span>}
                  {meta['year'] && <span>Year: <strong>{meta['year']}</strong></span>}
                  {meta['score'] && <span>Score: <strong>{Number(meta['score']).toFixed(3)}</strong></span>}
                </div>
              )}
              <p className="line-clamp-3 text-xs text-muted-foreground">{node.text}</p>
            </div>
          )
        })}
      </div>
    </details>
  )
}
