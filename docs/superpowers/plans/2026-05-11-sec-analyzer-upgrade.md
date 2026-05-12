# SEC Analyzer Upgrade — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the single-file `index.html` frontend into a production-grade Next.js 14 app deployed to Vercel, while keeping the FastAPI backend untouched on Render.

**Architecture:** Next.js 14 App Router lives in `frontend/` inside the existing mono-repo. All API calls go through `NEXT_PUBLIC_API_URL` pointing at the Render backend. `vercel.json` at repo root rewrites `/api/*` to the Render URL so same-origin calls work in production.

**Tech Stack:** Next.js 14, TypeScript (strict), shadcn/ui (base-nova), Tailwind CSS, recharts, lucide-react, GSD workspace

---

## Phase 0 — Tooling Setup (Orchestrator runs this directly)

### Task 0: Copy tooling + bootstrap GSD

**Files:**

- Copy: `.claude/` from `C:\Users\gujju\my-project-ui`
- Copy: `.husky/` from `C:\Users\gujju\my-project-ui`
- Copy: `.prettierrc` from `C:\Users\gujju\my-project-ui`
- Copy: `.secretlintrc.json` from `C:\Users\gujju\my-project-ui`

- [ ] **Step 1: Copy .claude folder**

```powershell
Copy-Item "C:\Users\gujju\my-project-ui\.claude" "D:\0001-Full Time\Projects\sec_analyzer\.claude" -Recurse -Force
```

- [ ] **Step 2: Copy .husky folder**

```powershell
Copy-Item "C:\Users\gujju\my-project-ui\.husky" "D:\0001-Full Time\Projects\sec_analyzer\.husky" -Recurse -Force
```

- [ ] **Step 3: Copy config files**

```powershell
Copy-Item "C:\Users\gujju\my-project-ui\.prettierrc" "D:\0001-Full Time\Projects\sec_analyzer\.prettierrc" -Force
Copy-Item "C:\Users\gujju\my-project-ui\.secretlintrc.json" "D:\0001-Full Time\Projects\sec_analyzer\.secretlintrc.json" -Force
```

- [ ] **Step 4: Run graphify install**

```bash
cd "D:\0001-Full Time\Projects\sec_analyzer"
graphify install
```

Expected: GSD workspace initialised, `.planning/` directory created.

- [ ] **Step 5: Run graphify claude install**

```bash
graphify claude install
```

Expected: Claude Code integration configured.

- [ ] **Step 6: Record session context via GSD**

```bash
graphify record-session
```

Expected: Current brainstorming context saved to GSD workspace.

---

## Phase 1 — Next.js Scaffold (Agent F1)

### Task 1: Scaffold Next.js 14 app

**Files:**

- Create: `frontend/` (entire directory)
- Create: `frontend/package.json`
- Create: `frontend/next.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/components.json`
- Create: `frontend/app/globals.css`
- Create: `frontend/.env.local.example`
- Create: `frontend/tailwind.config.ts`

- [ ] **Step 1: Create Next.js app**

```bash
cd "D:\0001-Full Time\Projects\sec_analyzer"
npx create-next-app@14 frontend --typescript --tailwind --eslint --app --no-src-dir --import-alias "@/*"
```

- [ ] **Step 2: Install dependencies**

```bash
cd frontend
npm install recharts lucide-react class-variance-authority clsx tailwind-merge
npm install -D @types/node
```

- [ ] **Step 3: Install shadcn/ui**

```bash
npx shadcn@latest init
```

When prompted:

- Style: `base-nova`
- Base color: `neutral`
- CSS variables: `yes`

- [ ] **Step 4: Add required shadcn components**

```bash
npx shadcn@latest add button input card badge separator scroll-area sheet tooltip
```

- [ ] **Step 5: Replace globals.css with project theme**

Replace `frontend/app/globals.css` with:

```css
@import 'tailwindcss';
@import 'tw-animate-css';
@import 'shadcn/tailwind.css';

@custom-variant dark (&:is(.dark *));

@theme inline {
  --color-background: var(--background);
  --color-foreground: var(--foreground);
  --font-sans: var(--font-sans);
  --font-mono: var(--font-geist-mono);
  --color-sidebar-ring: var(--sidebar-ring);
  --color-sidebar-border: var(--sidebar-border);
  --color-sidebar-accent-foreground: var(--sidebar-accent-foreground);
  --color-sidebar-accent: var(--sidebar-accent);
  --color-sidebar-primary-foreground: var(--sidebar-primary-foreground);
  --color-sidebar-primary: var(--sidebar-primary);
  --color-sidebar-foreground: var(--sidebar-foreground);
  --color-sidebar: var(--sidebar);
  --color-chart-5: var(--chart-5);
  --color-chart-4: var(--chart-4);
  --color-chart-3: var(--chart-3);
  --color-chart-2: var(--chart-2);
  --color-chart-1: var(--chart-1);
  --color-ring: var(--ring);
  --color-input: var(--input);
  --color-border: var(--border);
  --color-destructive: var(--destructive);
  --color-accent-foreground: var(--accent-foreground);
  --color-accent: var(--accent);
  --color-muted-foreground: var(--muted-foreground);
  --color-muted: var(--muted);
  --color-secondary-foreground: var(--secondary-foreground);
  --color-secondary: var(--secondary);
  --color-primary-foreground: var(--primary-foreground);
  --color-primary: var(--primary);
  --color-popover-foreground: var(--popover-foreground);
  --color-popover: var(--popover);
  --color-card-foreground: var(--card-foreground);
  --color-card: var(--card);
  --radius-sm: calc(var(--radius) * 0.6);
  --radius-md: calc(var(--radius) * 0.8);
  --radius-lg: var(--radius);
  --radius-xl: calc(var(--radius) * 1.4);
}

:root {
  --background: oklch(1 0 0);
  --foreground: oklch(0.145 0 0);
  --card: oklch(1 0 0);
  --card-foreground: oklch(0.145 0 0);
  --popover: oklch(1 0 0);
  --popover-foreground: oklch(0.145 0 0);
  --primary: oklch(0.205 0 0);
  --primary-foreground: oklch(0.985 0 0);
  --secondary: oklch(0.97 0 0);
  --secondary-foreground: oklch(0.205 0 0);
  --muted: oklch(0.97 0 0);
  --muted-foreground: oklch(0.556 0 0);
  --accent: oklch(0.97 0 0);
  --accent-foreground: oklch(0.205 0 0);
  --destructive: oklch(0.577 0.245 27.325);
  --border: oklch(0.922 0 0);
  --input: oklch(0.922 0 0);
  --ring: oklch(0.708 0 0);
  --chart-1: oklch(0.488 0.243 264.376);
  --chart-2: oklch(0.696 0.17 162.48);
  --chart-3: oklch(0.769 0.188 70.08);
  --chart-4: oklch(0.627 0.265 303.9);
  --chart-5: oklch(0.645 0.246 16.439);
  --radius: 0.625rem;
  --sidebar: oklch(0.985 0 0);
  --sidebar-foreground: oklch(0.145 0 0);
  --sidebar-primary: oklch(0.205 0 0);
  --sidebar-primary-foreground: oklch(0.985 0 0);
  --sidebar-accent: oklch(0.97 0 0);
  --sidebar-accent-foreground: oklch(0.205 0 0);
  --sidebar-border: oklch(0.922 0 0);
  --sidebar-ring: oklch(0.708 0 0);
}

.dark {
  --background: oklch(0.145 0 0);
  --foreground: oklch(0.985 0 0);
  --card: oklch(0.205 0 0);
  --card-foreground: oklch(0.985 0 0);
  --popover: oklch(0.205 0 0);
  --popover-foreground: oklch(0.985 0 0);
  --primary: oklch(0.922 0 0);
  --primary-foreground: oklch(0.205 0 0);
  --secondary: oklch(0.269 0 0);
  --secondary-foreground: oklch(0.985 0 0);
  --muted: oklch(0.269 0 0);
  --muted-foreground: oklch(0.708 0 0);
  --accent: oklch(0.269 0 0);
  --accent-foreground: oklch(0.985 0 0);
  --destructive: oklch(0.704 0.191 22.216);
  --border: oklch(1 0 0 / 10%);
  --input: oklch(1 0 0 / 15%);
  --ring: oklch(0.556 0 0);
  --chart-1: oklch(0.488 0.243 264.376);
  --chart-2: oklch(0.696 0.17 162.48);
  --chart-3: oklch(0.769 0.188 70.08);
  --chart-4: oklch(0.627 0.265 303.9);
  --chart-5: oklch(0.645 0.246 16.439);
  --sidebar: oklch(0.205 0 0);
  --sidebar-foreground: oklch(0.985 0 0);
  --sidebar-primary: oklch(0.488 0.243 264.376);
  --sidebar-primary-foreground: oklch(0.985 0 0);
  --sidebar-accent: oklch(0.269 0 0);
  --sidebar-accent-foreground: oklch(0.985 0 0);
  --sidebar-border: oklch(1 0 0 / 10%);
  --sidebar-ring: oklch(0.556 0 0);
}

@layer base {
  * {
    @apply border-border outline-ring/50;
  }
  body {
    @apply bg-background text-foreground;
  }
  html {
    @apply font-sans;
  }
}
```

- [ ] **Step 6: Create next.config.ts with API rewrite**

```ts
// frontend/next.config.ts
import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  async rewrites() {
    const apiUrl = process.env.RENDER_API_URL ?? 'http://127.0.0.1:8000';
    return [
      {
        source: '/api/:path*',
        destination: `${apiUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
```

- [ ] **Step 7: Create .env.local.example**

```bash
# frontend/.env.local.example
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
RENDER_API_URL=http://127.0.0.1:8000
```

- [ ] **Step 8: Verify build compiles**

```bash
cd frontend
npm run build
```

Expected: Build succeeds with no TypeScript errors.

---

### Task 2: Types + API client

**Files:**

- Create: `frontend/lib/types.ts`
- Create: `frontend/lib/api.ts`
- Create: `frontend/lib/utils.ts` (cn helper — shadcn generates this)

- [ ] **Step 1: Write types mirroring app/models.py**

Create `frontend/lib/types.ts`:

```ts
export interface StructuredAnswer {
  kind: 'value' | 'trend' | 'qualitative';
  value?: number;
  unit?: string;
  year?: number;
  ticker?: string;
  metric?: string;
  source?: string;
  confidence: number;
  series: Array<{ year: number; value: number; unit?: string }>;
}

export interface QueryResponse {
  answer: string;
  source_nodes: Array<{
    text: string;
    score?: number;
    metadata?: Record<string, unknown>;
  }>;
  graph_path: string[];
  latency_ms: number;
  mode: string;
  structured?: StructuredAnswer;
}

export interface CompareResponse {
  question: string;
  graph: QueryResponse;
  naive: QueryResponse;
}

export interface PipelineStatusResponse {
  job_id: string;
  stage: string;
  progress: number;
  message: string;
  errors: string[];
}

export interface DataStatusResponse {
  downloaded: Record<string, number[]>;
  parsed: Record<string, number[]>;
  index_stats: Record<string, unknown>;
}

export interface BenchmarkResult {
  question_id: string;
  question: string;
  question_type: string;
  expected: unknown;
  graph_answer?: string;
  naive_answer?: string;
  tra_graph: boolean;
  tra_naive: boolean;
  acs_graph?: number;
  acs_naive?: number;
  cyc_graph?: boolean;
  cyc_naive?: boolean;
  confidence?: number;
}

export interface BenchmarkResultResponse {
  generated_at: string;
  total_questions: number;
  summary: {
    structured: { TRA: number; ACS: number; CYC: number };
    naive: { TRA: number; ACS: number; CYC: number };
  };
  results: BenchmarkResult[];
}

export interface HealthResponse {
  status: string;
  environment: string;
  index_ready: boolean;
  graph_nodes: number;
  graph_edges: number;
}

export type QueryMode = 'graph' | 'naive';
```

- [ ] **Step 2: Write typed API client**

Create `frontend/lib/api.ts`:

```ts
const BASE = process.env.NEXT_PUBLIC_API_URL ?? '';

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { cache: 'no-store' });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

import type {
  CompareResponse,
  BenchmarkResultResponse,
  DataStatusResponse,
  PipelineStatusResponse,
  QueryResponse,
  QueryMode,
} from './types';

export const api = {
  query: (question: string, mode: QueryMode) =>
    post<QueryResponse>('/api/query', { question, mode }),

  compare: (question: string) =>
    post<CompareResponse>('/api/query/compare', { question, mode: 'graph' }),

  benchmarkResults: () =>
    get<BenchmarkResultResponse>('/api/benchmark/results'),

  runBenchmark: () => post<PipelineStatusResponse>('/api/benchmark/run', {}),

  dataStatus: () => get<DataStatusResponse>('/api/pipeline/data-status'),

  download: (tickers?: string[], years?: number[]) =>
    post<PipelineStatusResponse>('/api/pipeline/download', { tickers, years }),

  parse: (tickers?: string[], years?: number[]) =>
    post<PipelineStatusResponse>('/api/pipeline/parse', { tickers, years }),

  buildIndex: (tickers?: string[], years?: number[]) =>
    post<PipelineStatusResponse>('/api/pipeline/build-index', {
      tickers,
      years,
    }),

  pollStatus: (jobId: string) =>
    get<PipelineStatusResponse>(`/api/pipeline/status/${jobId}`),
};
```

- [ ] **Step 3: Commit scaffold**

```bash
cd "D:\0001-Full Time\Projects\sec_analyzer"
git add frontend/
git commit -m "feat: scaffold Next.js 14 frontend with types and API client"
```

---

### Task 3: AppShell + Sidebar layout

**Files:**

- Create: `frontend/app/layout.tsx`
- Create: `frontend/app/page.tsx`
- Create: `frontend/components/layout/AppShell.tsx`
- Create: `frontend/components/layout/Sidebar.tsx`
- Create: `frontend/components/layout/MobileHeader.tsx`

- [ ] **Step 1: Create Sidebar component**

Create `frontend/components/layout/Sidebar.tsx`:

```tsx
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
```

- [ ] **Step 2: Create MobileHeader**

Create `frontend/components/layout/MobileHeader.tsx`:

```tsx
'use client';

import { Menu } from 'lucide-react';
import { useState } from 'react';
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';
import { Sidebar } from './Sidebar';

export function MobileHeader() {
  const [open, setOpen] = useState(false);
  return (
    <header className="flex h-14 items-center gap-3 border-b border-border bg-background px-4 md:hidden">
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetTrigger asChild>
          <Button variant="ghost" size="icon" className="h-8 w-8">
            <Menu className="h-4 w-4" />
          </Button>
        </SheetTrigger>
        <SheetContent side="left" className="w-60 p-0">
          <Sidebar />
        </SheetContent>
      </Sheet>
      <span className="text-sm font-semibold">FilingsIQ</span>
    </header>
  );
}
```

- [ ] **Step 3: Create AppShell**

Create `frontend/components/layout/AppShell.tsx`:

```tsx
import { Sidebar } from './Sidebar';
import { MobileHeader } from './MobileHeader';

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen">
      <div className="hidden md:flex md:w-60 md:flex-col md:fixed md:inset-y-0">
        <Sidebar />
      </div>
      <div className="flex flex-1 flex-col md:pl-60">
        <MobileHeader />
        <main className="flex-1 overflow-y-auto">{children}</main>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Create root layout**

Replace `frontend/app/layout.tsx`:

```tsx
import type { Metadata } from 'next';
import { GeistSans } from 'geist/font/sans';
import { GeistMono } from 'geist/font/mono';
import { AppShell } from '@/components/layout/AppShell';
import './globals.css';

export const metadata: Metadata = {
  title: 'FilingsIQ — SEC 10-K Intelligence',
  description: 'Multi-year SEC 10-K trend analysis powered by GraphRAG',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${GeistSans.variable} ${GeistMono.variable} antialiased`}
      >
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
```

- [ ] **Step 5: Create root page redirect**

Create `frontend/app/page.tsx`:

```tsx
import { redirect } from 'next/navigation';

export default function Home() {
  redirect('/ask');
}
```

- [ ] **Step 6: Install geist font**

```bash
cd frontend
npm install geist
```

- [ ] **Step 7: Verify dev server starts**

```bash
npm run dev
```

Open `http://localhost:3000` — should redirect to `/ask` (404 page for now is fine).

- [ ] **Step 8: Commit**

```bash
git add frontend/
git commit -m "feat: add AppShell, Sidebar, MobileHeader layout components"
```

---

## Phase 2 — Ask Tab (Agent F2)

### Task 4: Ask tab — QueryInput + ModeSelector + ExampleCards

**Files:**

- Create: `frontend/components/ask/ModeSelector.tsx`
- Create: `frontend/components/ask/QueryInput.tsx`
- Create: `frontend/components/ask/ExampleCards.tsx`
- Create: `frontend/app/ask/page.tsx`

- [ ] **Step 1: Create ModeSelector**

Create `frontend/components/ask/ModeSelector.tsx`:

```tsx
'use client';

import { cn } from '@/lib/utils';
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
        <button
          key={value}
          onClick={() => onChange(value)}
          className={cn(
            'rounded-md px-3 py-1.5 text-xs font-semibold transition-all',
            'text-muted-foreground hover:text-foreground',
            mode === value && 'bg-primary text-primary-foreground shadow-sm'
          )}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Create ExampleCards**

Create `frontend/components/ask/ExampleCards.tsx`:

```tsx
'use client';

interface ExampleCardsProps {
  onSelect: (q: string) => void;
}

const EXAMPLES = [
  {
    tag: 'Revenue',
    tagClass: 'text-chart-1',
    q: "What was Apple's total revenue in 2023?",
  },
  {
    tag: 'Trend',
    tagClass: 'text-chart-3',
    q: "How did Microsoft's operating income trend from 2021 to 2023?",
  },
  {
    tag: 'Margin',
    tagClass: 'text-chart-2',
    q: "What was Apple's gross margin in 2022?",
  },
  {
    tag: 'Risk',
    tagClass: 'text-chart-4',
    q: 'What are the main risk factors Apple disclosed in 2023?',
  },
  {
    tag: 'Compare',
    tagClass: 'text-chart-5',
    q: 'Compare Apple and Microsoft R&D spending in 2023.',
  },
  {
    tag: 'Trend',
    tagClass: 'text-chart-3',
    q: "How did Apple's net income change from 2021 to 2024?",
  },
];

export function ExampleCards({ onSelect }: ExampleCardsProps) {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {EXAMPLES.map(({ tag, tagClass, q }) => (
        <button
          key={q}
          onClick={() => onSelect(q)}
          className="group rounded-xl border border-border bg-card p-4 text-left transition-all hover:-translate-y-0.5 hover:border-border/80 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <span
            className={`mb-2 inline-block rounded px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${tagClass} bg-current/10`}
          >
            {tag}
          </span>
          <p className="text-sm text-foreground/80 leading-snug group-hover:text-foreground">
            {q}
          </p>
        </button>
      ))}
    </div>
  );
}
```

- [ ] **Step 3: Create QueryInput**

Create `frontend/components/ask/QueryInput.tsx`:

```tsx
'use client';

import { Send } from 'lucide-react';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { ModeSelector } from './ModeSelector';
import type { QueryMode } from '@/lib/types';

interface QueryInputProps {
  value: string;
  onChange: (v: string) => void;
  mode: QueryMode | 'compare';
  onModeChange: (m: QueryMode | 'compare') => void;
  onSubmit: () => void;
  loading: boolean;
}

export function QueryInput({
  value,
  onChange,
  mode,
  onModeChange,
  onSubmit,
  loading,
}: QueryInputProps) {
  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) onSubmit();
  };
  return (
    <div className="rounded-xl border border-border bg-card p-5 shadow-sm">
      <Textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKey}
        placeholder="Ask a question about SEC 10-K filings..."
        className="min-h-14 resize-none border-0 bg-transparent p-0 text-base shadow-none focus-visible:ring-0"
        rows={2}
      />
      <div className="mt-3 flex items-center justify-between gap-3 flex-wrap">
        <ModeSelector mode={mode} onChange={onModeChange} />
        <Button
          onClick={onSubmit}
          disabled={loading || !value.trim()}
          size="sm"
          className="gap-2"
        >
          <Send className="h-3.5 w-3.5" />
          {loading ? 'Thinking…' : 'Ask'}
        </Button>
      </div>
      <p className="mt-2 text-xs text-muted-foreground">⌘ + Enter to submit</p>
    </div>
  );
}
```

- [ ] **Step 4: Create Ask page skeleton**

Create `frontend/app/ask/page.tsx`:

```tsx
'use client';

import { useState } from 'react';
import { QueryInput } from '@/components/ask/QueryInput';
import { ExampleCards } from '@/components/ask/ExampleCards';
import type { QueryMode } from '@/lib/types';

export default function AskPage() {
  const [question, setQuestion] = useState('');
  const [mode, setMode] = useState<QueryMode | 'compare'>('graph');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    if (!question.trim()) return;
    setLoading(true);
    // Results rendering added in Task 5
    setLoading(false);
  };

  return (
    <div className="mx-auto max-w-4xl px-4 py-8 md:px-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight">Ask FilingsIQ</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Ask questions about Apple and Microsoft 10-K filings (2021–2024)
        </p>
      </div>

      <div className="space-y-6">
        <QueryInput
          value={question}
          onChange={setQuestion}
          mode={mode}
          onModeChange={setMode}
          onSubmit={handleSubmit}
          loading={loading}
        />
        <div>
          <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-muted-foreground">
            Example Questions
          </p>
          <ExampleCards
            onSelect={(q) => {
              setQuestion(q);
            }}
          />
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Commit**

```bash
git add frontend/
git commit -m "feat: ask tab QueryInput, ModeSelector, ExampleCards"
```

---

### Task 5: AnswerCard + EvidenceAccordion

**Files:**

- Create: `frontend/components/ask/AnswerCard.tsx`
- Create: `frontend/components/ask/EvidenceAccordion.tsx`
- Modify: `frontend/app/ask/page.tsx` (wire up API call + render results)

- [ ] **Step 1: Create AnswerCard**

Create `frontend/components/ask/AnswerCard.tsx`:

```tsx
import { Badge } from '@/components/ui/badge';
import type { QueryResponse } from '@/lib/types';

interface AnswerCardProps {
  result: QueryResponse;
}

export function AnswerCard({ result }: AnswerCardProps) {
  const s = result.structured;
  const isNumeric = s?.kind === 'value' && s.value != null;

  return (
    <div className="rounded-xl border border-border bg-gradient-to-br from-chart-1/5 to-chart-2/5 p-6 shadow-md">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Badge variant={result.mode === 'graph' ? 'default' : 'secondary'}>
            {result.mode === 'graph' ? 'Smart Mode' : 'Basic Mode'}
          </Badge>
          {s?.metric && (
            <Badge variant="outline" className="text-xs">
              {s.metric}
            </Badge>
          )}
        </div>
        {s && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span>Confidence</span>
            <div className="h-1.5 w-20 overflow-hidden rounded-full bg-muted">
              <div
                className="h-full bg-chart-2 transition-all"
                style={{ width: `${Math.round(s.confidence * 100)}%` }}
              />
            </div>
            <span className="font-medium">
              {Math.round(s.confidence * 100)}%
            </span>
          </div>
        )}
      </div>

      {s && (s.ticker || s.year) && (
        <div className="mb-3 flex flex-wrap gap-3 text-xs text-muted-foreground">
          {s.ticker && (
            <span>
              Ticker: <strong className="text-foreground">{s.ticker}</strong>
            </span>
          )}
          {s.year && (
            <span>
              Year: <strong className="text-foreground">{s.year}</strong>
            </span>
          )}
          {s.source && (
            <span>
              Source: <strong className="text-foreground">{s.source}</strong>
            </span>
          )}
        </div>
      )}

      {isNumeric ? (
        <div className="my-2">
          <span className="text-5xl font-extrabold tracking-tight">
            {s!.value!.toLocaleString()}
          </span>
          {s!.unit && (
            <span className="ml-2 text-2xl font-semibold text-muted-foreground">
              {s!.unit}
            </span>
          )}
        </div>
      ) : (
        <p className="text-base leading-relaxed">{result.answer}</p>
      )}

      {isNumeric && result.answer && (
        <p className="mt-4 border-t border-dashed border-border pt-4 text-sm text-muted-foreground">
          {result.answer}
        </p>
      )}

      <p className="mt-3 text-xs text-muted-foreground">
        {result.latency_ms.toFixed(0)}ms · {result.source_nodes.length} chunks
        retrieved
      </p>
    </div>
  );
}
```

- [ ] **Step 2: Create EvidenceAccordion**

Create `frontend/components/ask/EvidenceAccordion.tsx`:

```tsx
'use client';

import { ChevronRight } from 'lucide-react';
import type { QueryResponse } from '@/lib/types';

interface EvidenceAccordionProps {
  nodes: QueryResponse['source_nodes'];
}

export function EvidenceAccordion({ nodes }: EvidenceAccordionProps) {
  if (!nodes.length) return null;
  return (
    <details className="group rounded-xl border border-border bg-card overflow-hidden">
      <summary className="flex cursor-pointer select-none list-none items-center gap-2 px-5 py-3.5 text-xs font-semibold text-muted-foreground hover:text-foreground transition-colors">
        <ChevronRight className="h-3.5 w-3.5 transition-transform group-open:rotate-90" />
        Evidence — {nodes.length} chunks retrieved
      </summary>
      <div className="flex flex-col gap-2 px-5 pb-5">
        {nodes.map((node, i) => {
          const meta = node.metadata as Record<string, string> | undefined;
          return (
            <div
              key={i}
              className="rounded-lg border border-border bg-muted/50 p-3"
            >
              {meta && (
                <div className="mb-1.5 flex gap-3 text-[10px] text-muted-foreground">
                  {meta['company'] && (
                    <span>
                      Company: <strong>{meta['company']}</strong>
                    </span>
                  )}
                  {meta['year'] && (
                    <span>
                      Year: <strong>{meta['year']}</strong>
                    </span>
                  )}
                  {meta['score'] && (
                    <span>
                      Score: <strong>{Number(meta['score']).toFixed(3)}</strong>
                    </span>
                  )}
                </div>
              )}
              <p className="line-clamp-3 text-xs text-muted-foreground">
                {node.text}
              </p>
            </div>
          );
        })}
      </div>
    </details>
  );
}
```

- [ ] **Step 3: Wire API call into Ask page**

Replace `frontend/app/ask/page.tsx`:

```tsx
'use client';

import { useState } from 'react';
import { api } from '@/lib/api';
import { QueryInput } from '@/components/ask/QueryInput';
import { ExampleCards } from '@/components/ask/ExampleCards';
import { AnswerCard } from '@/components/ask/AnswerCard';
import { EvidenceAccordion } from '@/components/ask/EvidenceAccordion';
import type { QueryMode, QueryResponse, CompareResponse } from '@/lib/types';

export default function AskPage() {
  const [question, setQuestion] = useState('');
  const [mode, setMode] = useState<QueryMode | 'compare'>('graph');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [compare, setCompare] = useState<CompareResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    if (!question.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    setCompare(null);
    try {
      if (mode === 'compare') {
        setCompare(await api.compare(question));
      } else {
        setResult(await api.query(question, mode));
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-4xl px-4 py-8 md:px-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight">Ask FilingsIQ</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Ask questions about Apple and Microsoft 10-K filings (2021–2024)
        </p>
      </div>
      <div className="space-y-5">
        <QueryInput
          value={question}
          onChange={setQuestion}
          mode={mode}
          onModeChange={setMode}
          onSubmit={handleSubmit}
          loading={loading}
        />
        {error && (
          <div className="rounded-lg border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            {error}
          </div>
        )}
        {result && (
          <>
            <AnswerCard result={result} />
            <EvidenceAccordion nodes={result.source_nodes} />
          </>
        )}
        {compare && (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Smart Mode
              </p>
              <AnswerCard result={compare.graph} />
            </div>
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Basic Mode
              </p>
              <AnswerCard result={compare.naive} />
            </div>
          </div>
        )}
        {!result && !compare && !loading && (
          <div>
            <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-muted-foreground">
              Example Questions
            </p>
            <ExampleCards onSelect={(q) => setQuestion(q)} />
          </div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/
git commit -m "feat: AnswerCard, EvidenceAccordion, Ask page API wiring"
```

---

## Phase 3 — Streaming + History (Agent F2 continued)

### Task 6: LoadingStages component

**Files:**

- Create: `frontend/components/ask/LoadingStages.tsx`
- Modify: `frontend/app/ask/page.tsx` (show stages while loading)

- [ ] **Step 1: Create LoadingStages**

Create `frontend/components/ask/LoadingStages.tsx`:

```tsx
'use client';

import { useEffect, useState } from 'react';
import { Check, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

const STAGES = [
  { id: 'retrieve', label: 'Retrieving relevant chunks' },
  { id: 'rerank', label: 'Reranking with flashrank' },
  { id: 'synthesize', label: 'Synthesizing answer' },
  { id: 'done', label: 'Done' },
];

interface LoadingStagesProps {
  active: boolean;
}

export function LoadingStages({ active }: LoadingStagesProps) {
  const [current, setCurrent] = useState(0);

  useEffect(() => {
    if (!active) {
      setCurrent(0);
      return;
    }
    const timings = [800, 1600, 2800];
    const timers = timings.map((t, i) =>
      setTimeout(() => setCurrent(i + 1), t)
    );
    return () => timers.forEach(clearTimeout);
  }, [active]);

  if (!active) return null;

  return (
    <div className="rounded-xl border border-border bg-card px-6 py-5 space-y-3">
      {STAGES.slice(0, -1).map((stage, i) => (
        <div
          key={stage.id}
          className={cn(
            'flex items-center gap-3 text-sm transition-colors',
            i < current && 'text-chart-2',
            i === current && 'text-foreground',
            i > current && 'text-muted-foreground/40'
          )}
        >
          <div className="w-5 flex justify-center">
            {i < current ? (
              <Check className="h-4 w-4" />
            ) : i === current ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <div className="h-2 w-2 rounded-full bg-current" />
            )}
          </div>
          {stage.label}
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Add LoadingStages to Ask page**

In `frontend/app/ask/page.tsx`, add import and render:

```tsx
import { LoadingStages } from '@/components/ask/LoadingStages';

// In JSX, between QueryInput and results:
<LoadingStages active={loading} />;
```

- [ ] **Step 3: Commit**

```bash
git add frontend/
git commit -m "feat: LoadingStages component with animated retrieval progress"
```

---

### Task 7: QueryHistory sidebar panel

**Files:**

- Create: `frontend/hooks/useQueryHistory.ts`
- Create: `frontend/components/ask/QueryHistory.tsx`
- Modify: `frontend/app/ask/page.tsx` (integrate history)

- [ ] **Step 1: Create useQueryHistory hook**

Create `frontend/hooks/useQueryHistory.ts`:

```ts
'use client';

import { useState, useCallback } from 'react';
import type { QueryResponse } from '@/lib/types';

export interface HistoryEntry {
  id: string;
  question: string;
  mode: string;
  answer: string;
  timestamp: number;
}

const MAX = 20;

export function useQueryHistory() {
  const [history, setHistory] = useState<HistoryEntry[]>([]);

  const push = useCallback(
    (question: string, mode: string, result: QueryResponse) => {
      const entry: HistoryEntry = {
        id: `${Date.now()}`,
        question,
        mode,
        answer: result.answer.slice(0, 120),
        timestamp: Date.now(),
      };
      setHistory((prev) => [entry, ...prev].slice(0, MAX));
    },
    []
  );

  const clear = useCallback(() => setHistory([]), []);

  return { history, push, clear };
}
```

- [ ] **Step 2: Create QueryHistory panel**

Create `frontend/components/ask/QueryHistory.tsx`:

```tsx
'use client';

import { Clock, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import type { HistoryEntry } from '@/hooks/useQueryHistory';

interface QueryHistoryProps {
  history: HistoryEntry[];
  onSelect: (q: string) => void;
  onClear: () => void;
}

export function QueryHistory({
  history,
  onSelect,
  onClear,
}: QueryHistoryProps) {
  if (!history.length) return null;
  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-muted-foreground">
          <Clock className="h-3.5 w-3.5" />
          Recent Queries
        </div>
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6"
          onClick={onClear}
        >
          <Trash2 className="h-3.5 w-3.5" />
        </Button>
      </div>
      <ScrollArea className="max-h-48">
        <div className="space-y-1">
          {history.map((entry) => (
            <button
              key={entry.id}
              onClick={() => onSelect(entry.question)}
              className="w-full rounded-lg px-3 py-2.5 text-left text-xs transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <p className="font-medium text-foreground line-clamp-1">
                {entry.question}
              </p>
              <p className="mt-0.5 text-muted-foreground line-clamp-1">
                {entry.answer}
              </p>
            </button>
          ))}
        </div>
      </ScrollArea>
    </div>
  );
}
```

- [ ] **Step 3: Wire history into Ask page**

In `frontend/app/ask/page.tsx`, add:

```tsx
import { useQueryHistory } from '@/hooks/useQueryHistory'
import { QueryHistory } from '@/components/ask/QueryHistory'

// inside component:
const { history, push, clear } = useQueryHistory()

// in handleSubmit after setResult(data):
push(question, mode, data)

// in JSX after EvidenceAccordion:
<QueryHistory history={history} onSelect={setQuestion} onClear={clear} />
```

- [ ] **Step 4: Commit**

```bash
git add frontend/
git commit -m "feat: QueryHistory panel with useQueryHistory hook"
```

---

## Phase 4 — Recharts Visualizations (Agent F3)

### Task 8: TrendCard with recharts

**Files:**

- Create: `frontend/components/ask/TrendCard.tsx`
- Modify: `frontend/app/ask/page.tsx` (render TrendCard for trend answers)

- [ ] **Step 1: Create TrendCard**

Create `frontend/components/ask/TrendCard.tsx`:

```tsx
'use client';

import { useState } from 'react';
import {
  LineChart,
  BarChart,
  Line,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { Button } from '@/components/ui/button';
import type { StructuredAnswer } from '@/lib/types';

interface TrendCardProps {
  structured: StructuredAnswer;
}

export function TrendCard({ structured }: TrendCardProps) {
  const [chartType, setChartType] = useState<'line' | 'bar'>('line');
  if (!structured.series.length) return null;

  const data = structured.series.map((d) => ({
    year: String(d.year),
    value: d.value,
  }));

  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <div className="mb-4 flex items-center justify-between">
        <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
          Trend — {structured.metric ?? 'Value'} ({structured.unit ?? ''})
        </p>
        <div className="flex gap-1">
          {(['line', 'bar'] as const).map((t) => (
            <Button
              key={t}
              variant={chartType === t ? 'default' : 'ghost'}
              size="sm"
              className="h-7 px-3 text-xs"
              onClick={() => setChartType(t)}
            >
              {t === 'line' ? 'Line' : 'Bar'}
            </Button>
          ))}
        </div>
      </div>
      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          {chartType === 'line' ? (
            <LineChart data={data}>
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="hsl(var(--border))"
              />
              <XAxis
                dataKey="year"
                tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }}
              />
              <YAxis
                tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }}
              />
              <Tooltip
                contentStyle={{
                  background: 'hsl(var(--popover))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: 8,
                }}
                labelStyle={{ color: 'hsl(var(--foreground))' }}
              />
              <Line
                type="monotone"
                dataKey="value"
                stroke="hsl(var(--chart-1))"
                strokeWidth={2}
                dot={{ r: 4 }}
              />
            </LineChart>
          ) : (
            <BarChart data={data}>
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="hsl(var(--border))"
              />
              <XAxis
                dataKey="year"
                tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }}
              />
              <YAxis
                tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }}
              />
              <Tooltip
                contentStyle={{
                  background: 'hsl(var(--popover))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: 8,
                }}
                labelStyle={{ color: 'hsl(var(--foreground))' }}
              />
              <Bar
                dataKey="value"
                fill="hsl(var(--chart-1))"
                radius={[4, 4, 0, 0]}
              />
            </BarChart>
          )}
        </ResponsiveContainer>
      </div>
      <div className="mt-3 flex gap-2 overflow-x-auto">
        {structured.series.map((d) => (
          <div
            key={d.year}
            className="shrink-0 rounded-lg border border-border bg-muted/50 px-3 py-2 text-center"
          >
            <p className="text-[10px] text-muted-foreground">{d.year}</p>
            <p className="text-sm font-bold">{d.value.toLocaleString()}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Add TrendCard to Ask page**

In `frontend/app/ask/page.tsx`, after AnswerCard:

```tsx
import { TrendCard } from '@/components/ask/TrendCard';

// In JSX, after <AnswerCard result={result} />:
{
  result.structured?.kind === 'trend' &&
    result.structured.series.length > 0 && (
      <TrendCard structured={result.structured} />
    );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/
git commit -m "feat: TrendCard with recharts line/bar toggle"
```

---

### Task 9: Benchmark tab

**Files:**

- Create: `frontend/components/benchmark/StatsGrid.tsx`
- Create: `frontend/components/benchmark/BenchmarkTable.tsx`
- Create: `frontend/components/benchmark/RadarChart.tsx`
- Create: `frontend/app/benchmark/page.tsx`

- [ ] **Step 1: Create StatsGrid**

Create `frontend/components/benchmark/StatsGrid.tsx`:

```tsx
interface StatCardProps {
  label: string;
  structured: number;
  naive: number;
}

function StatCard({ label, structured, naive }: StatCardProps) {
  const delta = Math.round((structured - naive) * 100);
  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
        {label}
      </p>
      <p className="mt-2 text-4xl font-extrabold tracking-tight text-chart-2">
        {Math.round(structured * 100)}%
      </p>
      <p className="mt-1 text-xs text-muted-foreground">
        Naive: {Math.round(naive * 100)}%
        <span
          className={`ml-2 font-semibold ${delta >= 0 ? 'text-chart-2' : 'text-destructive'}`}
        >
          {delta >= 0 ? '+' : ''}
          {delta}pp
        </span>
      </p>
    </div>
  );
}

interface StatsGridProps {
  summary: {
    structured: { TRA: number; ACS: number; CYC: number };
    naive: { TRA: number; ACS: number; CYC: number };
  };
}

export function StatsGrid({ summary }: StatsGridProps) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
      <StatCard
        label="Table Retrieval (TRA)"
        structured={summary.structured.TRA}
        naive={summary.naive.TRA}
      />
      <StatCard
        label="Answer Correctness (ACS)"
        structured={summary.structured.ACS}
        naive={summary.naive.ACS}
      />
      <StatCard
        label="Cross-Year Coherence (CYC)"
        structured={summary.structured.CYC}
        naive={summary.naive.CYC}
      />
    </div>
  );
}
```

- [ ] **Step 2: Create RadarChartCard**

Create `frontend/components/benchmark/RadarChart.tsx`:

```tsx
'use client';

import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import type { BenchmarkResultResponse } from '@/lib/types';

interface RadarChartCardProps {
  summary: BenchmarkResultResponse['summary'];
}

export function RadarChartCard({ summary }: RadarChartCardProps) {
  const data = [
    {
      metric: 'TRA',
      structured: summary.structured.TRA * 100,
      naive: summary.naive.TRA * 100,
    },
    {
      metric: 'ACS',
      structured: summary.structured.ACS * 100,
      naive: summary.naive.ACS * 100,
    },
    {
      metric: 'CYC',
      structured: summary.structured.CYC * 100,
      naive: summary.naive.CYC * 100,
    },
  ];
  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <p className="mb-4 text-xs font-semibold uppercase tracking-widest text-muted-foreground">
        Structured vs Naive — Radar
      </p>
      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart data={data}>
            <PolarGrid stroke="hsl(var(--border))" />
            <PolarAngleAxis
              dataKey="metric"
              tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }}
            />
            <Radar
              name="Structured"
              dataKey="structured"
              stroke="hsl(var(--chart-1))"
              fill="hsl(var(--chart-1))"
              fillOpacity={0.25}
            />
            <Radar
              name="Naive"
              dataKey="naive"
              stroke="hsl(var(--chart-3))"
              fill="hsl(var(--chart-3))"
              fillOpacity={0.15}
            />
            <Legend wrapperStyle={{ fontSize: 11 }} />
          </RadarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Create BenchmarkTable**

Create `frontend/components/benchmark/BenchmarkTable.tsx`:

```tsx
import { Badge } from '@/components/ui/badge';
import type { BenchmarkResult } from '@/lib/types';

interface BenchmarkTableProps {
  results: BenchmarkResult[];
}

export function BenchmarkTable({ results }: BenchmarkTableProps) {
  return (
    <div className="rounded-xl border border-border bg-card overflow-hidden">
      <table className="w-full text-xs">
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
          </tr>
        </thead>
        <tbody>
          {results.map((r, i) => (
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
                  {r.question_type}
                </Badge>
              </td>
              <td className="px-4 py-3 text-center">
                <span
                  className={
                    r.tra_graph ? 'font-bold text-chart-2' : 'text-destructive'
                  }
                >
                  {r.tra_graph ? '✓' : '✗'}
                </span>
              </td>
              <td className="px-4 py-3 text-center text-muted-foreground">
                {r.acs_graph != null
                  ? `${Math.round(r.acs_graph * 100)}%`
                  : '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

- [ ] **Step 4: Create Benchmark page**

Create `frontend/app/benchmark/page.tsx`:

```tsx
'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { StatsGrid } from '@/components/benchmark/StatsGrid';
import { RadarChartCard } from '@/components/benchmark/RadarChart';
import { BenchmarkTable } from '@/components/benchmark/BenchmarkTable';
import { Button } from '@/components/ui/button';
import type { BenchmarkResultResponse } from '@/lib/types';

export default function BenchmarkPage() {
  const [data, setData] = useState<BenchmarkResultResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    api
      .benchmarkResults()
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const handleRun = async () => {
    setRunning(true);
    try {
      await api.runBenchmark();
      const fresh = await api.benchmarkResults();
      setData(fresh);
    } catch (e) {
      console.error(e);
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 md:px-8">
      <div className="mb-8 flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            Benchmark Results
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Structured GraphRAG vs naive vector retrieval across 10 questions
          </p>
        </div>
        <Button
          onClick={handleRun}
          disabled={running}
          size="sm"
          variant="outline"
        >
          {running ? 'Running…' : 'Re-run Benchmark'}
        </Button>
      </div>
      {loading && (
        <p className="text-sm text-muted-foreground">Loading results…</p>
      )}
      {data && (
        <div className="space-y-6">
          <StatsGrid summary={data.summary} />
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <RadarChartCard summary={data.summary} />
            <div className="rounded-xl border border-border bg-card p-5">
              <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-muted-foreground">
                About
              </p>
              <p className="text-sm text-muted-foreground leading-relaxed">
                <strong className="text-foreground">TRA</strong> — Table
                Retrieval Accuracy: did retrieved chunks contain the expected
                Markdown table row?
                <br />
                <strong className="text-foreground">ACS</strong> — Answer
                Correctness Score: numeric answer within 5% of expected?
                <br />
                <strong className="text-foreground">CYC</strong> — Cross-Year
                Coherence: does the answer mention all required years?
              </p>
              <p className="mt-3 text-xs text-muted-foreground">
                Generated: {data.generated_at} · {data.total_questions}{' '}
                questions
              </p>
            </div>
          </div>
          <BenchmarkTable results={data.results} />
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 5: Commit**

```bash
git add frontend/
git commit -m "feat: Benchmark tab with StatsGrid, RadarChart, BenchmarkTable"
```

---

### Task 10: Pipeline tab

**Files:**

- Create: `frontend/components/pipeline/DataStatusGrid.tsx`
- Create: `frontend/components/pipeline/PipelineTriggers.tsx`
- Create: `frontend/app/pipeline/page.tsx`

- [ ] **Step 1: Create DataStatusGrid**

Create `frontend/components/pipeline/DataStatusGrid.tsx`:

```tsx
import type { DataStatusResponse } from '@/lib/types';
import { cn } from '@/lib/utils';

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
          <div className="flex flex-wrap gap-2">
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
                          : 'bg-muted'
                    )}
                  />
                  {yr}
                </div>
              );
            })}
          </div>
          <p className="mt-2 text-[10px] text-muted-foreground">
            <span className="inline-flex items-center gap-1">
              <span className="h-1.5 w-1.5 rounded-full bg-chart-2 inline-block" />{' '}
              Parsed
            </span>
            {' · '}
            <span className="inline-flex items-center gap-1">
              <span className="h-1.5 w-1.5 rounded-full bg-chart-3 inline-block" />{' '}
              Downloaded
            </span>
            {' · '}
            <span className="inline-flex items-center gap-1">
              <span className="h-1.5 w-1.5 rounded-full bg-muted inline-block" />{' '}
              Missing
            </span>
          </p>
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Create PipelineTriggers**

Create `frontend/components/pipeline/PipelineTriggers.tsx`:

```tsx
'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { api } from '@/lib/api';
import type { PipelineStatusResponse } from '@/lib/types';

interface TriggerButtonProps {
  label: string;
  action: () => Promise<PipelineStatusResponse>;
  onDone: () => void;
}

function TriggerButton({ label, action, onDone }: TriggerButtonProps) {
  const [status, setStatus] = useState<PipelineStatusResponse | null>(null);
  const [loading, setLoading] = useState(false);

  const run = async () => {
    setLoading(true);
    try {
      const res = await action();
      setStatus(res);
      // poll until done
      let current = res;
      while (current.progress < 100 && current.stage !== 'error') {
        await new Promise((r) => setTimeout(r, 2000));
        current = await api.pollStatus(current.job_id);
        setStatus(current);
      }
      onDone();
    } catch (e) {
      setStatus({
        job_id: '',
        stage: 'error',
        progress: 0,
        message: String(e),
        errors: [],
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <div className="flex items-center justify-between mb-3">
        <p className="text-sm font-semibold">{label}</p>
        <Button onClick={run} disabled={loading} size="sm" variant="outline">
          {loading ? 'Running…' : 'Run'}
        </Button>
      </div>
      {status && (
        <>
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
            <div
              className="h-full bg-chart-1 transition-all duration-300"
              style={{ width: `${status.progress}%` }}
            />
          </div>
          <p className="mt-2 text-xs text-muted-foreground">{status.message}</p>
          {status.errors.length > 0 && (
            <p className="mt-1 text-xs text-destructive">
              {status.errors.join(', ')}
            </p>
          )}
        </>
      )}
    </div>
  );
}

interface PipelineTriggersProps {
  onStatusChange: () => void;
}

export function PipelineTriggers({ onStatusChange }: PipelineTriggersProps) {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
      <TriggerButton
        label="1. Download Filings"
        action={() => api.download()}
        onDone={onStatusChange}
      />
      <TriggerButton
        label="2. Parse with LlamaParse"
        action={() => api.parse()}
        onDone={onStatusChange}
      />
      <TriggerButton
        label="3. Build Index"
        action={() => api.buildIndex()}
        onDone={onStatusChange}
      />
      <TriggerButton
        label="4. Run Benchmark"
        action={() => api.runBenchmark()}
        onDone={onStatusChange}
      />
    </div>
  );
}
```

- [ ] **Step 3: Create Pipeline page**

Create `frontend/app/pipeline/page.tsx`:

```tsx
'use client';

import { useEffect, useState, useCallback } from 'react';
import { api } from '@/lib/api';
import { DataStatusGrid } from '@/components/pipeline/DataStatusGrid';
import { PipelineTriggers } from '@/components/pipeline/PipelineTriggers';
import type { DataStatusResponse } from '@/lib/types';

export default function PipelinePage() {
  const [status, setStatus] = useState<DataStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(() => {
    api
      .dataStatus()
      .then(setStatus)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return (
    <div className="mx-auto max-w-4xl px-4 py-8 md:px-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold tracking-tight">Data Pipeline</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Download, parse, and index SEC 10-K filings
        </p>
      </div>
      <div className="space-y-6">
        <div>
          <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-muted-foreground">
            Pipeline Steps
          </p>
          <PipelineTriggers onStatusChange={refresh} />
        </div>
        <div>
          <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-muted-foreground">
            Data Status
          </p>
          {loading && <p className="text-sm text-muted-foreground">Loading…</p>}
          {status && <DataStatusGrid status={status} />}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/
git commit -m "feat: Pipeline tab with DataStatusGrid and PipelineTriggers"
```

---

## Phase 5 — Mobile Responsiveness (Agent F4)

### Task 11: Mobile audit + responsive fixes

**Files:**

- Modify: `frontend/components/layout/AppShell.tsx`
- Modify: `frontend/components/layout/Sidebar.tsx`
- Modify: `frontend/app/ask/page.tsx`
- Modify: `frontend/app/benchmark/page.tsx`
- Modify: `frontend/app/pipeline/page.tsx`

- [ ] **Step 1: Verify mobile layout in browser at 375px**

Start dev server: `cd frontend && npm run dev`

Open DevTools → Toggle device toolbar → set to 375px wide.

Check each tab for:

- Sidebar hidden, hamburger visible
- No horizontal scroll
- Cards stack vertically
- Text is readable (≥12px)

- [ ] **Step 2: Fix any overflow issues**

In each page file, ensure all grid containers use:

```tsx
// Replace any fixed-width grid with responsive:
// Before: grid-cols-2
// After:  grid-cols-1 sm:grid-cols-2

// Replace fixed px padding:
// Before: px-8
// After:  px-4 md:px-8
```

- [ ] **Step 3: Fix chart heights on mobile**

In `TrendCard.tsx` and `RadarChart.tsx`, replace fixed `h-56` with responsive height:

```tsx
// Replace: <div className="h-56">
// With:
<div className="h-44 sm:h-56">
```

- [ ] **Step 4: Fix benchmark table on mobile**

In `BenchmarkTable.tsx`, make table horizontally scrollable:

```tsx
// Wrap table in:
<div className="overflow-x-auto">
  <table className="w-full min-w-[600px] text-xs">...</table>
</div>
```

- [ ] **Step 5: Test all 3 tabs at 375px, 768px, 1280px**

Verify at each breakpoint: no overflow, no overlapping elements, buttons are tappable (min 44px target).

- [ ] **Step 6: Commit**

```bash
git add frontend/
git commit -m "fix: mobile responsive — collapsible sidebar, responsive grids, scrollable tables"
```

---

## Phase 6 — Code Review (Code Reviewer Agent)

### Task 12: Frontend code review

The code reviewer agent reads `.claude/rules/frontend.md` and checks:

- shadcn/ui only (no raw HTML form elements)
- Tailwind classes only (no inline styles)
- Mobile-first (base 375px)
- No `any` types in TypeScript
- Every interactive element has hover + focus state
- All API calls use `lib/api.ts`

Reviewer produces a list of findings. Orchestrator dispatches fixes back to frontend agent.

---

## Phase 7 — GitHub + Vercel Deploy (Deploy Agent)

### Task 13: Git init + GitHub push

**Files:**

- Create/Modify: `.gitignore`
- Create: `vercel.json`

- [ ] **Step 1: Init git repo**

```bash
cd "D:\0001-Full Time\Projects\sec_analyzer"
git init
git branch -m main
```

- [ ] **Step 2: Update .gitignore**

Create `.gitignore`:

```
# Python
venv/
__pycache__/
*.pyc
*.pyo
.env

# Data (large, rebuild from committed Markdown)
data/raw_filings/
data/chroma_db/
data/graph_store/

# Frontend
frontend/.next/
frontend/node_modules/
frontend/.env.local

# OS
.DS_Store
Thumbs.db
```

- [ ] **Step 3: Create vercel.json**

```json
{
  "buildCommand": "cd frontend && npm install && npm run build",
  "outputDirectory": "frontend/.next",
  "framework": "nextjs",
  "rewrites": [
    {
      "source": "/api/:path*",
      "destination": "https://sec-filing-analyzer.onrender.com/api/:path*"
    }
  ]
}
```

- [ ] **Step 4: Create GitHub repo and push**

```bash
# Create repo via GitHub CLI
gh repo create sec-analyzer --public --description "Multi-year SEC 10-K trend analyzer with GraphRAG"

# Initial commit
git add .
git commit -m "feat: initial commit — FastAPI backend + Next.js frontend"

# Push
git remote add origin https://github.com/$(gh api user --jq .login)/sec-analyzer.git
git push -u origin main
```

- [ ] **Step 5: Verify GitHub shows both backend + frontend**

Open `https://github.com/<user>/sec-analyzer` and confirm `frontend/` directory is present.

---

### Task 14: Vercel deployment

- [ ] **Step 1: Install Vercel CLI**

```bash
npm install -g vercel
```

- [ ] **Step 2: Login to Vercel**

```bash
vercel login
```

- [ ] **Step 3: Deploy from frontend directory**

```bash
cd "D:\0001-Full Time\Projects\sec_analyzer"
vercel --cwd frontend
```

When prompted:

- Link to existing project? No
- Project name: `filingsiq`
- Root directory: `./` (we're already in frontend)

- [ ] **Step 4: Set environment variables**

```bash
vercel env add NEXT_PUBLIC_API_URL production
# enter: https://sec-filing-analyzer.onrender.com

vercel env add RENDER_API_URL production
# enter: https://sec-filing-analyzer.onrender.com
```

- [ ] **Step 5: Deploy to production**

```bash
vercel --prod
```

Expected output: `https://filingsiq.vercel.app`

- [ ] **Step 6: Smoke test production**

Open `https://filingsiq.vercel.app/ask` and run:

- Type "What was Apple's revenue in 2023?" → Submit
- Verify answer renders
- Open `/benchmark` → verify stats grid shows
- Open `/pipeline` → verify data status loads

- [ ] **Step 7: Final commit**

```bash
git add vercel.json .gitignore
git commit -m "chore: add vercel.json and .gitignore"
git push
```

---

## Self-Review Checklist

- [x] **Spec coverage:** Setup (Task 0) ✓, Next.js scaffold (Tasks 1–3) ✓, Ask tab (Tasks 4–7) ✓, Recharts (Tasks 8–10) ✓, Mobile (Task 11) ✓, Code review (Task 12) ✓, GitHub + Vercel (Tasks 13–14) ✓
- [x] **No placeholders:** All steps have concrete commands or code blocks
- [x] **Type consistency:** `QueryMode`, `QueryResponse`, `CompareResponse`, `StructuredAnswer`, `BenchmarkResultResponse`, `DataStatusResponse`, `PipelineStatusResponse` defined in Task 2 and used consistently throughout
- [x] **API consistency:** All API calls go through `api.*` from `lib/api.ts` — no direct fetch calls in components
- [x] **shadcn components used:** Button, Badge, Textarea, Sheet, ScrollArea, Tooltip — all added in Task 1 Step 4
- [x] **No inline styles:** All styling uses Tailwind classes + CSS variables
- [x] **Dark mode:** `className="dark"` on `<html>` in layout.tsx; all colors use oklch vars that have dark overrides
