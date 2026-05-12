# /security-check

Run a full security audit on the current codebase.

## Usage

```
/security-check
```

Optionally scope to a path: `/security-check src/api`

## Steps

### 1. Secret Scanning

```bash
# Look for hardcoded secrets, tokens, keys
grep -rn "api_key\|apikey\|secret\|password\|token\|AUTH_\|SK_\|pk_" --include="*.js" --include="*.ts" --include="*.json" . \
  | grep -v "node_modules\|.env\|test\|spec\|example"
```

Flag any matches that are not environment variable references.

### 2. Input Validation Audit

- Check all HTTP request handlers for unvalidated user input
- Confirm server-side validation exists (not just client-side)
- Look for `eval()`, `exec()`, `shell`, `child_process` with user-controlled data

### 3. Dependency Audit

```bash
npm audit
```

Report any `high` or `critical` severity vulnerabilities.

### 4. OWASP Top 10 Spot Check

Using the `code-reviewer` agent, scan for:

- SQL / NoSQL injection
- XSS (unescaped output to DOM)
- Broken access control (missing auth checks)
- Security misconfiguration (CORS, headers, error messages leaking stack traces)
- Insecure direct object references

### 5. Auth & Payment Boundary Check

Verify that `/src/auth/**` and `/src/payments/**` are not called from client-side code.

## Output Format

Report findings grouped by severity:

```
## CRITICAL
- [file:line] description

## HIGH
- [file:line] description

## MEDIUM / INFO
- [file:line] description

## PASSED
- List of checks that found no issues
```

If no issues found, state that explicitly — do not leave the report empty.
