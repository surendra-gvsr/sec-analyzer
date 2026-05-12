# /fix-issue

Fix a GitHub issue by number.

## Usage

```
/fix-issue <issue-number>
```

## Steps

1. **Fetch issue details**

   ```bash
   gh issue view $ARGUMENTS --json number,title,body,labels,comments,assignees
   ```

2. **Understand the problem** — read the title, body, reproduction steps, and all comments before touching any code

3. **Identify affected files** — grep and glob for relevant code; read `.claude/memory/known-gotchas.md` for traps

4. **Plan the fix** — if scope is 3+ steps, enter Plan mode and present the plan before writing code

5. **Write a failing test first** — reproduce the bug in a test, confirm it fails

6. **Implement the fix** — make the test pass with minimal changes; do not refactor unrelated code

7. **Run verification**

   ```bash
   npm test
   npm run typecheck
   ```

8. **Commit** referencing the issue
   ```
   fix(<scope>): <summary> (closes #<issue-number>)
   ```

## Rules

- Never touch `/src/auth/**`, `/src/payments/**`, or `.env.*` without explicit approval
- If the issue is ambiguous, ask one clarifying question before starting
- If tests don't exist for the affected area, add them
