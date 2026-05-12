# /deploy-check

Verify the app is safe and ready to push before deploying.

## Usage

```
/deploy-check
```

## Steps

### 1. Run Tests

```bash
npm test
```

- All tests must pass. If any fail, stop and report — do not continue.

### 2. Type Check

```bash
npm run typecheck
```

- Zero type errors required before proceeding.

### 3. Secret Scan

```bash
grep -rn "api_key\|apikey\|secret\|password\|token\|AUTH_\|SK_\|pk_" --include="*.js" --include="*.ts" . \
  | grep -v "node_modules\|.env\|test\|spec\|example\|process\.env"
```

- Any hardcoded secrets = immediate stop. Do not proceed to push.

### 4. Check Unstaged / Uncommitted Changes

```bash
git status
git diff --stat
```

- Warn if there are uncommitted changes that would not be included in the push.

### 5. Verify No Forbidden Patterns

- No `console.log` left in production paths (warn, don't block)
- No `TODO: remove before deploy` comments
- No `debugger` statements

### 6. Review Outgoing Commits

```bash
git log origin/main..HEAD --oneline
```

- Summarize what will be pushed so the user can confirm scope.

## Final Verdict

Output one of:

```
✅ READY TO PUSH
All checks passed. Commits going out: [list]
```

or

```
❌ NOT READY
Blocking issues:
- [description]

Warnings (non-blocking):
- [description]
```

Never push automatically — always wait for explicit user confirmation after showing the verdict.
