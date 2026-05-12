'use client';

import { Button } from '@/components/ui/button';
import type { QueryMode } from '@/lib/types';

interface ModeSelectorProps {
  mode: QueryMode | 'compare';
  onChange: (m: QueryMode | 'compare') => void;
}

const MODES: { value: QueryMode | 'compare'; label: string }[] = [
  { value: 'graph', label: 'Smart' },
  { value: 'naive', label: 'Basic' },
  { value: 'compare', label: 'Compare' },
];

export function ModeSelector({ mode, onChange }: ModeSelectorProps) {
  return (
    <div className="flex gap-1 rounded-lg border border-border bg-muted p-1">
      {MODES.map(({ value, label }) => (
        <Button
          key={value}
          variant={mode === value ? 'default' : 'ghost'}
          size="sm"
          onClick={() => onChange(value)}
          className="h-7 px-3 text-xs"
        >
          {label}
        </Button>
      ))}
    </div>
  );
}
