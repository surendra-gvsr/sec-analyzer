'use client';

const EXAMPLES = [
  {
    tag: 'Revenue',
    tagColor: 'text-blue-400 bg-blue-400/10',
    q: "What was Apple's total revenue in 2023?",
  },
  {
    tag: 'Trend',
    tagColor: 'text-orange-400 bg-orange-400/10',
    q: "How did Microsoft's operating income trend from 2021 to 2023?",
  },
  {
    tag: 'Margin',
    tagColor: 'text-green-400 bg-green-400/10',
    q: "What was Apple's gross margin in 2022?",
  },
  {
    tag: 'Risk',
    tagColor: 'text-red-400 bg-red-400/10',
    q: 'What are the main risk factors Apple disclosed in 2023?',
  },
  {
    tag: 'Compare',
    tagColor: 'text-purple-400 bg-purple-400/10',
    q: 'Compare Apple and Microsoft R&D spending in 2023.',
  },
  {
    tag: 'Trend',
    tagColor: 'text-orange-400 bg-orange-400/10',
    q: "How did Apple's net income change from 2021 to 2024?",
  },
];

interface ExampleCardsProps {
  onSelect: (q: string) => void;
}

export function ExampleCards({ onSelect }: ExampleCardsProps) {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {EXAMPLES.map(({ tag, tagColor, q }) => (
        <button
          key={q}
          type="button"
          onClick={() => onSelect(q)}
          className="group flex flex-col items-start gap-2 rounded-xl border border-border bg-card p-4 text-left transition-all hover:-translate-y-0.5 hover:border-border/60 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <span
            className={`rounded px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${tagColor}`}
          >
            {tag}
          </span>
          <p className="text-sm text-muted-foreground leading-snug group-hover:text-foreground transition-colors">
            {q}
          </p>
        </button>
      ))}
    </div>
  );
}
