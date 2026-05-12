# Frontend Code Review — 2026-05-11

**Reviewed:** 2026-05-11  
**Depth:** standard (all listed files read in full)  
**Files Reviewed:** 24  
**Status:** NEEDS_FIXES

---

## Strengths

- **Clean separation of concerns.** Each file has one clear responsibility; pages orchestrate, components render, hooks encapsulate state. No page-level logic is leaked into leaf components.
- **No hardcoded API URLs.** All calls go through `lib/api.ts` which falls back to an empty string (relative paths) when `NEXT_PUBLIC_API_URL` is absent — correct behaviour for same-origin deploys.
- **Type safety is largely solid.** `strict: true` in `tsconfig.json`, no `any` escapes in business code, `Record<string, unknown>` used correctly for opaque metadata.
- **Accessibility basics present.** `focus-visible` ring classes on every interactive element, `sr-only` close label in Sheet, `list-none` on `<summary>` to suppress browser arrow.
- **Dark-mode tokens are complete.** `globals.css` defines both `:root` and `.dark` for every design token; `hsl(var(--*))` usage in recharts tooltips resolves correctly at runtime.
- **Error states handled.** `ask/page.tsx` surfaces a styled error block; `PipelineTriggers` shows error text inline; benchmark and pipeline pages log errors (correctly using `console.error`).
- **Polling loop is bounded.** `PipelineTriggers` exits the while loop on both `progress === 100` and `stage === 'error'`, preventing infinite polling.
- **History capped at 20 entries.** `useQueryHistory` slices to `MAX` on insert, preventing unbounded growth.

---

## Critical Issues

### CR-01: `SheetTrigger` render prop API misuse — mobile nav hamburger is broken

**File:** `components/layout/MobileHeader.tsx:13-18`

`SheetTrigger` is a `@base-ui/react` Dialog trigger. The Base UI `Dialog.Trigger` component accepts a `render` prop that replaces its default element; it does **not** accept children that are rendered inside a wrapping trigger element like Radix does.

The current code passes a `<Button>` as `render` but then places `<Menu className="h-4 w-4" />` as a **child of `SheetTrigger`**, not as a child of the `Button` render slot. Base UI's trigger implementation calls `render` to produce the trigger element and threads its own props through — the children of `SheetTrigger` (the `<Menu>` icon) are silently discarded and never rendered. The hamburger menu button will appear as an empty, icon-less button on mobile.

```tsx
// BROKEN — Menu icon is a child of SheetTrigger, not of the rendered Button
<SheetTrigger
  render={<Button variant="ghost" size="icon" className="h-8 w-8" />}
>
  <Menu className="h-4 w-4" /> {/* discarded */}
</SheetTrigger>
```

**Fix:** Pass the icon inside the `render` prop's element:

```tsx
<SheetTrigger
  render={
    <Button
      variant="ghost"
      size="icon"
      className="h-8 w-8"
      aria-label="Open navigation"
    >
      <Menu className="h-4 w-4" />
    </Button>
  }
/>
```

---

### CR-02: Infinite polling if API never returns `progress === 100` or `stage === 'error'`

**File:** `components/pipeline/PipelineTriggers.tsx:24`

The polling loop guard is:

```ts
while (current.progress < 100 && current.stage !== 'error') {
```

If the backend returns a job that stalls — for example, `progress` stays at 95 and `stage` is `'running'` indefinitely — the loop polls forever. There is no timeout, no iteration counter, and no user-facing cancel mechanism. On the Groq free tier described in `CLAUDE.md`, a pipeline run can hit a 429 or 413 and the job may never complete, leaving the UI locked with `loading: true` and a spinning button that can never be clicked again (the `run` function does `setLoading(true)` but only `setLoading(false)` in `finally`, which only fires when the loop exits).

**Fix:** Add a maximum iteration count (or a wall-clock deadline):

```ts
const MAX_POLLS = 150; // 5 minutes at 2s interval
let polls = 0;
while (
  current.progress < 100 &&
  current.stage !== 'error' &&
  polls < MAX_POLLS
) {
  await new Promise((r) => setTimeout(r, 2000));
  current = await api.pollStatus(current.job_id);
  setStatus(current);
  polls++;
}
if (polls >= MAX_POLLS) {
  setStatus({
    job_id: current.job_id,
    stage: 'error',
    progress: current.progress,
    message: 'Timed out waiting for job to complete.',
    errors: [],
  });
}
```

---

### CR-03: `AnswerCard` — missing `isNumeric` guard causes `s!` non-null assertions to be reachable as null/undefined

**File:** `components/ask/AnswerCard.tsx:48-50`

The condition on line 45 is `if (isNumeric)` where `isNumeric = s?.kind === 'value' && s.value != null`. Inside the `isNumeric` branch the code uses `s!.value!.toLocaleString()` and `s!.unit`. TypeScript allows this because `isNumeric` is a `boolean` variable, not a type narrowing expression, so the compiler does not propagate the truthiness of `s?.value != null` into the JSX branch. At runtime this is safe only because `isNumeric` is evaluated again at branch entry — **but only if the component re-renders between state changes**. If `s` mutates to `null` between the `isNumeric` computation and the render (possible in Concurrent Mode with `startTransition`), `s!.value!` will throw.

More immediately, the secondary render on line 58:

```tsx
{isNumeric && result.answer && (
  <p ...>{result.answer}</p>
)}
```

uses `result.answer` unchecked — `result.answer` is typed `string` (non-optional) in `QueryResponse`, so this is safe. But `s!.unit` on line 50 is accessed with the non-null assertion while `unit` is typed `string | undefined` in `StructuredAnswer`. If `kind === 'value'` and `unit` is undefined, `s!.unit` returns `undefined` correctly, so this is fine. The real risk is at line 48: `s!.value!.toLocaleString()`. If the API sends `{ kind: 'value', value: null }`, both `isNumeric` is false (correct) and the branch is skipped — but the non-null assertion `s!.value!` stays in source and will bite if the guard condition is ever loosened.

**Fix:** Replace the boolean variable with a type predicate / explicit null check inside JSX to avoid the force-unwrap:

```tsx
{
  s?.kind === 'value' && s.value != null ? (
    <div className="my-2">
      <span className="text-5xl font-extrabold tracking-tight">
        {s.value.toLocaleString()}
      </span>
      {s.unit && (
        <span className="ml-2 text-2xl font-semibold text-muted-foreground">
          {s.unit}
        </span>
      )}
    </div>
  ) : (
    <p className="text-base leading-relaxed">{result.answer}</p>
  );
}
```

---

### CR-04: `BenchmarkPage.handleRun` — no user-visible error feedback

**File:** `app/benchmark/page.tsx:20-30`

`handleRun` catches errors and calls `console.error(e)` only. The user pressing "Re-run Benchmark" will see the button return to "Re-run Benchmark" state with no indication that the run failed (e.g. Groq 429, network error). The component has no `error` state. Given `CLAUDE.md` explicitly calls out that heavy iteration burns the daily Groq budget and produces 429s for ~24h, this is a likely failure path that leaves the user with no actionable information.

**Fix:** Add an error state and render it below the button:

```tsx
const [error, setError] = useState<string | null>(null);

const handleRun = async () => {
  setRunning(true);
  setError(null);
  try {
    await api.runBenchmark();
    const fresh = await api.benchmarkResults();
    setData(fresh);
  } catch (e) {
    setError(e instanceof Error ? e.message : 'Benchmark run failed');
  } finally {
    setRunning(false);
  }
};
```

---

## Important Issues (Warnings)

### WR-01: `DataStatusGrid` shows tickers from `downloaded` only — if a ticker appears in `parsed` but not `downloaded`, it is invisible

**File:** `components/pipeline/DataStatusGrid.tsx:11`

```ts
const tickers = Object.keys(status.downloaded);
```

The grid is keyed entirely off `status.downloaded`. If the backend ever returns a `parsed` entry for a ticker that has no corresponding `downloaded` entry (e.g. pre-existing parsed files without a raw filing in the download cache), that ticker is not rendered at all, and its `parsed` status indicators are silently dropped. This is a data integrity display bug.

**Fix:**

```ts
const tickers = Array.from(
  new Set([...Object.keys(status.downloaded), ...Object.keys(status.parsed)])
).sort();
```

---

### WR-02: `EvidenceAccordion` casts `node.metadata` to `Record<string, string>` but the type is `Record<string, unknown>`

**File:** `components/ask/EvidenceAccordion.tsx:20`

```tsx
const meta = node.metadata as Record<string, string> | undefined;
```

`node.metadata` is typed `Record<string, unknown>` in `types.ts`. The cast to `Record<string, string>` is a lie — values could be numbers, booleans, or objects. Then on line 27:

```tsx
{
  meta['score'] && (
    <span>
      Score: <strong>{Number(meta['score']).toFixed(3)}</strong>
    </span>
  );
}
```

This wraps the value in `Number()` presumably because the author knew the score might be a number already — but the cast to `string` suppresses the TypeScript warning. If `meta['company']` is an object (e.g. `{ name: "Apple" }`), it renders `[object Object]` in the UI.

**Fix:** Keep the type honest and coerce to string for display:

```tsx
const meta = node.metadata; // Record<string, unknown> | undefined
// Then:
{
  meta?.['company'] != null && (
    <span>
      Company: <strong>{String(meta['company'])}</strong>
    </span>
  );
}
{
  meta?.['score'] != null && (
    <span>
      Score: <strong>{Number(meta['score']).toFixed(3)}</strong>
    </span>
  );
}
```

---

### WR-03: `useQueryHistory` — `id` collision risk when two queries are submitted within the same millisecond

**File:** `hooks/useQueryHistory.ts:21`

```ts
id: `${Date.now()}`,
```

`Date.now()` has millisecond resolution. If the user submits two queries in rapid succession (or in test automation), both entries get the same `id`, which is used as the React `key` in `QueryHistory`. Duplicate keys cause React to silently drop one entry from the DOM.

**Fix:** Use a monotonic counter or `crypto.randomUUID()`:

```ts
let _seq = 0
// inside push:
id: `${Date.now()}-${++_seq}`,
```

Or simply:

```ts
id: crypto.randomUUID(),
```

---

### WR-04: `LoadingStages` — animation does not reset when a second query is submitted while loading

**File:** `components/ask/LoadingStages.tsx:21-27`

```ts
useEffect(() => {
  if (!active) {
    setCurrent(0);
    return;
  }
  const timings = [800, 1600, 2800];
  const timers = timings.map((t, i) => setTimeout(() => setCurrent(i + 1), t));
  return () => timers.forEach(clearTimeout);
}, [active]);
```

The effect depends only on `active`. If the user submits a query, waits 1.5 seconds (stage 2 advances to `current=2`), then submits another query, `active` remains `true` throughout. The effect never re-fires, so `current` stays at 2 and the animation skips stage 1. The user sees the reranking stage already checked off before retrieval completes.

**Fix:** Add a query identity signal (e.g. an incrementing `queryKey` prop) to the dependency array so the effect re-fires on each new submission:

```tsx
// In ask/page.tsx:
const [queryKey, setQueryKey] = useState(0)
// In handleSubmit:
setQueryKey(k => k + 1)

// In LoadingStages:
interface LoadingStagesProps { active: boolean; queryKey: number }
useEffect(() => { ... }, [active, queryKey])
```

---

### WR-05: `TrendCard` — recharts `dot` prop uses `as object` cast to silence a type error

**File:** `components/ask/TrendCard.tsx:64`

```tsx
dot={{ r: 4, fill: 'hsl(var(--chart-1))' } as object}
```

`as object` is used to suppress a TypeScript error because recharts' `DotProps` interface doesn't accept arbitrary SVG attributes on the plain-object shorthand. This is a type escape hatch that silences a real mismatch. At runtime recharts may silently drop unrecognized properties or throw depending on the version.

**Fix:** Use a custom dot renderer instead of the object shorthand:

```tsx
dot={(props) => {
  const { cx, cy } = props
  return <circle cx={cx} cy={cy} r={4} fill="hsl(var(--chart-1))" />
}}
```

---

### WR-06: `ModeSelector` buttons are raw `<button>` elements — violates the rule "always use shadcn/ui components"

**File:** `components/ask/ModeSelector.tsx:21`

The frontend rules (`rules/frontend.md`) explicitly state: "Always use shadcn/ui components, never build from scratch." `ModeSelector` renders three raw `<button>` elements styled manually with Tailwind. The project has a `Button` component that already handles focus rings, disabled states, and variant styling.

**Fix:** Replace each `<button>` with `<Button variant={mode === value ? 'default' : 'ghost'} size="sm">`.

---

### WR-07: `ExampleCards` uses raw `<button>` — same rule violation as WR-06

**File:** `components/ask/ExampleCards.tsx:20`

Same issue: raw `<button>` styled from scratch. The button has correct `focus-visible` handling, but this pattern diverges from the project rule.

**Fix:** Wrap each example card in `<Button variant="ghost" className="h-auto w-full ...">` or extract a `CardButton` variant.

---

### WR-08: `QueryHistory` — clear button has no accessible label

**File:** `components/ask/QueryHistory.tsx:23`

```tsx
<Button
  variant="ghost"
  size="icon"
  className="h-6 w-6 hover:text-destructive"
  onClick={onClear}
>
  <Trash2 className="h-3.5 w-3.5" />
</Button>
```

This is an icon-only button with no `aria-label` and no `<span className="sr-only">` text. Screen readers will announce it as "button" with no context. The `SheetContent` close button in `sheet.tsx` correctly uses `<span className="sr-only">Close</span>`.

**Fix:**

```tsx
<Button
  variant="ghost"
  size="icon"
  className="h-6 w-6 hover:text-destructive"
  onClick={onClear}
  aria-label="Clear query history"
>
  <Trash2 className="h-3.5 w-3.5" />
</Button>
```

---

### WR-09: `BenchmarkTable` — CYC column missing from table

**File:** `components/benchmark/BenchmarkTable.tsx:14-20`

The table renders `#`, `Question`, `Type`, `TRA`, and `ACS` columns, but omits `CYC` (Cross-Year Coherence). The `BenchmarkResult` type has `cyc_graph` and `cyc_naive` fields, and `CLAUDE.md` describes CYC as the headline metric where structured beats naive. The `StatsGrid` and `RadarChart` display it, but the per-question table does not, meaning users cannot see which individual questions drove the CYC score.

**Fix:** Add a `CYC` column analogous to `TRA`:

```tsx
<th className="px-4 py-3 text-center ...">CYC</th>
// In each row:
<td className="px-4 py-3 text-center">
  {r.cyc_graph != null
    ? <span className={r.cyc_graph ? 'font-bold text-chart-2' : 'text-destructive'}>
        {r.cyc_graph ? '✓' : '✗'}
      </span>
    : <span className="text-muted-foreground">—</span>
  }
</td>
```

---

### WR-10: `compare` mode history push stores `data.graph` answer but mode stored as `'compare'`

**File:** `app/ask/page.tsx:35`

```ts
push(question, mode, data.graph);
```

When mode is `'compare'`, the history entry's `answer` is populated from `data.graph.answer` (the structured/smart mode answer). The naive answer is silently dropped. A user who selects a history entry from a compare run will see only the graph-mode answer in the history display, with no indication that a comparison was run. This is misleading.

**Fix:** Either push two entries (one per mode), or push a combined entry with a truncated diff:

```ts
push(question, 'graph', data.graph);
push(question, 'naive', data.naive);
```

Or accept the limitation and document it with a comment so the next developer understands the design decision.

---

### WR-11: `app/benchmark/page.tsx` — `handleRun` calls `api.runBenchmark()` then immediately calls `api.benchmarkResults()` without polling for completion

**File:** `app/benchmark/page.tsx:21-24`

```ts
await api.runBenchmark();
const fresh = await api.benchmarkResults();
setData(fresh);
```

`api.runBenchmark()` returns a `PipelineStatusResponse` with a `job_id`, but the page discards it and immediately fetches results. The benchmark run is async on the server side — `runBenchmark` starts the job, it does not block until completion. Fetching results immediately after will return the **previous** benchmark results, not the freshly computed ones. The `PipelineTriggers` component correctly implements polling; this page does not.

**Fix:** After `runBenchmark()` resolves, poll `api.pollStatus(jobId)` until `progress === 100` or `stage === 'error'`, then fetch results — mirroring the pattern in `PipelineTriggers`. Alternatively, add a `setRunning` state message like "Benchmark running, please wait…" and refresh manually.

---

## Minor Issues

### IN-01: `AnswerCard` — `latency_ms.toFixed(0)` could throw if `latency_ms` is undefined at runtime

**File:** `components/ask/AnswerCard.tsx:65`

`QueryResponse.latency_ms` is typed as `number` (non-optional), so TypeScript does not complain. However, if the backend omits the field, `undefined.toFixed()` will throw at runtime. A defensive `(result.latency_ms ?? 0).toFixed(0)` costs nothing.

---

### IN-02: `globals.css` imports `shadcn/tailwind.css` but `shadcn` is a CLI package, not a CSS provider

**File:** `app/globals.css:3`

```css
@import 'shadcn/tailwind.css';
```

The `shadcn` package in `package.json` is the CLI tool (`"shadcn": "^4.7.0"`). It does not ship a `tailwind.css` file for runtime import — the CSS comes from the component files themselves and Tailwind's scan. This import will fail at build time unless a `shadcn/tailwind.css` file is generated by the shadcn CLI into `node_modules/shadcn/`. Verify this file exists; if not, remove the import.

---

### IN-03: `Sidebar` — `path.startsWith(href)` matches `/ask` against `/` if `/` is ever added to NAV

**File:** `components/layout/Sidebar.tsx:35`

```ts
path.startsWith(href);
```

This is currently safe because all nav hrefs are `/ask`, `/benchmark`, `/pipeline` — none is `/`. But `path.startsWith('/')` is always true for any path, so if a root link is ever added, all nav items would appear active simultaneously. A more robust check: `path === href || path.startsWith(href + '/')`.

---

### IN-04: `QueryInput` keyboard hint is Mac-only

**File:** `components/ask/QueryInput.tsx:39`

```tsx
<p className="mt-2 text-xs text-muted-foreground">⌘ + Enter to submit</p>
```

The handler accepts both `metaKey` (Mac) and `ctrlKey` (Windows/Linux), but the UI hint only shows `⌘ + Enter`. Windows and Linux users will never discover `Ctrl + Enter` works.

**Fix:**

```tsx
<p className="mt-2 text-xs text-muted-foreground">
  {typeof navigator !== 'undefined' && /Mac/.test(navigator.platform)
    ? '⌘ + Enter to submit'
    : 'Ctrl + Enter to submit'}
</p>
```

Or simply: `Cmd/Ctrl + Enter to submit`.

---

### IN-05: `PipelineTriggers` — Run Benchmark button triggers `api.runBenchmark()` which is not a pipeline step

**File:** `components/pipeline/PipelineTriggers.tsx:73`

Step 4 "Run Benchmark" is wired to `api.runBenchmark()` which returns a `PipelineStatusResponse`. But `api.runBenchmark()` in `lib/api.ts` POSTs to `/api/benchmark/run`, not to a pipeline endpoint. The benchmark run does not have the same polling contract as the other pipeline steps (download/parse/build-index). If the benchmark endpoint returns a different job schema or completes synchronously, the polling loop will misbehave (e.g. if `job_id` is empty, `api.pollStatus('')` will call `/api/pipeline/status/` which is likely a 404).

**Fix:** Either give the benchmark its own UI path (as the Benchmark page does), or confirm the `/api/benchmark/run` endpoint returns a job object compatible with the polling contract and document that assumption.

---

### IN-06: Spacing scale violations — non-standard `py-3.5`, `gap-3`, `gap-1.5` values used widely

**File:** Multiple components

The project rules specify a spacing scale of `4, 8, 12, 16, 24, 32, 48, 64px only` (Tailwind equivalents: `1, 2, 3, 4, 6, 8, 12, 16`). Files use `py-3.5` (14px), `gap-3` (12px — this one is allowed), `gap-1.5` (6px), `gap-0.5` (2px), `px-5` (20px), `py-4` (16px — allowed), `py-2.5` (10px), and `h-1.5` (6px). The half-step values (`3.5`, `1.5`, `0.5`, `2.5`) fall outside the allowed scale. This is a style convention violation, not a runtime bug.

---

### IN-07: `console.error` calls in production pages without user feedback

**File:** `app/benchmark/page.tsx:17`, `app/pipeline/page.tsx:15`

```ts
api.benchmarkResults().then(setData).catch(console.error).finally(...)
api.dataStatus().then(setStatus).catch(console.error).finally(...)
```

These use `console.error` (allowed per rules) but provide no user-facing error message when the initial data load fails. The page renders blank with only "Loading results…" disappearing, leaving the user with an empty page and no explanation. At minimum, an error state should be rendered.

---

## Assessment

**NEEDS_FIXES**

The implementation is architecturally sound, well-typed, and demonstrates strong React patterns. However, there are two blockers that must be resolved before deploy:

1. **CR-01** makes the mobile hamburger menu non-functional (no icon, likely no interaction) on all mobile viewports.
2. **CR-02** allows the UI to lock indefinitely on stalled pipeline jobs — a realistic scenario given the Groq rate limits documented in `CLAUDE.md`.
3. **CR-04** and **WR-11** together mean the Benchmark "Re-run" workflow silently fails or returns stale data in the most likely error scenarios.

The remaining warnings (WR-01 through WR-10) are quality issues worth fixing before a public-facing deploy.

---

_Reviewed: 2026-05-11_  
_Reviewer: Claude (adversarial code review)_  
_Depth: standard_
