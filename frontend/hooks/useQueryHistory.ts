'use client'

import { useState, useCallback, useRef } from 'react'
import type { QueryResponse } from '@/lib/types'

export interface HistoryEntry {
  id: string
  question: string
  mode: string
  answer: string
  timestamp: number
}

const MAX = 20

export function useQueryHistory() {
  const [history, setHistory] = useState<HistoryEntry[]>([])
  const counterRef = useRef(0)

  const push = useCallback((question: string, mode: string, result: QueryResponse) => {
    const entry: HistoryEntry = {
      id: String(++counterRef.current),
      question,
      mode,
      answer: result.answer.slice(0, 120),
      timestamp: Date.now(),
    }
    setHistory(prev => [entry, ...prev].slice(0, MAX))
  }, [])

  const clear = useCallback(() => setHistory([]), [])

  return { history, push, clear }
}
