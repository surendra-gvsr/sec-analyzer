'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { MessageSquare, BarChart2, Settings2 } from 'lucide-react';
import { cn } from '@/lib/utils';

const NAV = [
  { href: '/ask', label: 'Ask', icon: MessageSquare },
  { href: '/benchmark', label: 'Benchmark', icon: BarChart2 },
  { href: '/pipeline', label: 'Pipeline', icon: Settings2 },
];

export function Sidebar() {
  const path = usePathname();
  return (
    <aside className="flex h-full w-60 flex-col border-r border-border bg-sidebar">
      <div className="flex items-center gap-3 border-b border-sidebar-border px-5 py-4">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-sidebar-primary text-sm font-bold text-sidebar-primary-foreground">
          IQ
        </div>
        <div>
          <p className="text-sm font-semibold text-sidebar-foreground">
            FilingsIQ
          </p>
          <p className="text-xs text-muted-foreground">SEC 10-K Intelligence</p>
        </div>
      </div>
      <nav className="flex-1 px-3 py-4 space-y-1">
        {NAV.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={cn(
              'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
              'text-sidebar-foreground/60 hover:bg-sidebar-accent hover:text-sidebar-foreground',
              path.startsWith(href) &&
                'bg-sidebar-accent text-sidebar-foreground shadow-[inset_2px_0_0_hsl(var(--sidebar-primary))]'
            )}
          >
            <Icon className="h-4 w-4 shrink-0" />
            {label}
          </Link>
        ))}
      </nav>
      <div className="border-t border-sidebar-border px-5 py-3 text-xs text-muted-foreground">
        GraphRAG · Groq · ChromaDB
      </div>
    </aside>
  );
}
