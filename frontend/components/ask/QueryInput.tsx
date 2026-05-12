'use client'

import { Send } from 'lucide-react'
import { Textarea } from '@/components/ui/textarea'
import { Button } from '@/components/ui/button'
import { ModeSelector } from './ModeSelector'
import type { QueryMode } from '@/lib/types'

interface QueryInputProps {
  value: string
  onChange: (v: string) => void
  mode: QueryMode | 'compare'
  onModeChange: (m: QueryMode | 'compare') => void
  onSubmit: () => void
  loading: boolean
}

export function QueryInput({ value, onChange, mode, onModeChange, onSubmit, loading }: QueryInputProps) {
  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) onSubmit()
  }
  return (
    <div className="rounded-xl border border-border bg-card p-5 shadow-sm">
      <Textarea
        value={value}
        onChange={e => onChange(e.target.value)}
        onKeyDown={handleKey}
        placeholder="Ask a question about SEC 10-K filings..."
        className="min-h-14 resize-none border-0 bg-transparent p-0 text-base shadow-none focus-visible:ring-0"
        rows={2}
      />
      <div className="mt-3 flex items-center justify-between gap-3 flex-wrap">
        <ModeSelector mode={mode} onChange={onModeChange} />
        <Button onClick={onSubmit} disabled={loading || !value.trim()} size="sm" className="gap-2">
          <Send className="h-3.5 w-3.5" />
          {loading ? 'Thinking…' : 'Ask'}
        </Button>
      </div>
      <p className="mt-2 text-xs text-muted-foreground">⌘ + Enter to submit</p>
    </div>
  )
}
