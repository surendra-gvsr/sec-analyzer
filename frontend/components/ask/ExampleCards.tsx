'use client';

import { Button } from '@/components/ui/button';

interface ExampleCardsProps {
  onSelect: (q: string) => void;
}

const EXAMPLES = [
  {
    tag: 'Revenue',
    tagColor: 'text-chart-1 bg-chart-1/10',
    q: "What was Apple's total revenue in 2023?",
  },
  {
    tag: 'Trend',
    tagColor: 'text-chart-3 bg-chart-3/10',
    q: "How did Microsoft's operating income trend from 2021 to 2023?",
  },
  {
    tag: 'Margin',
    tagColor: 'text-chart-2 bg-chart-2/10',
    q: "What was Apple's gross margin in 2022?",
  },
  {
    tag: 'Risk',
    tagColor: 'text-chart-4 bg-chart-4/10',
    q: 'What are the main risk factors Apple disclosed in 2023?',
  },
  {
    tag: 'Compare',
    tagColor: 'text-chart-5 bg-chart-5/10',
    q: 'Compare Apple and Microsoft R&D spending in 2023.',
  },
  {
    tag: 'Trend',
    tagColor: 'text-chart-3 bg-chart-3/10',
    q: "How did Apple's net income change from 2021 to 2024?",
  },
];

export function ExampleCards({ onSelect }: ExampleCardsProps) {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {EXAMPLES.map(({ tag, tagColor, q }) => (
        <Button
          key={q}
          variant="ghost"
          onClick={() => onSelect(q)}
          className="group h-auto w-full rounded-xl border border-border bg-card p-4 text-left transition-all hover:-translate-y-0.5 hover:border-border/60 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <span
            className={`mb-2 inline-block rounded px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${tagColor}`}
          >
            {tag}
          </span>
          <p className="text-sm text-muted-foreground leading-snug group-hover:text-foreground transition-colors">
            {q}
          </p>
        </Button>
      ))}
    </div>
  );
}
