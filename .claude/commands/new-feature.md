# /new-feature

Plan and build a new feature using the right sub-agents.

## Usage

```
/new-feature <description>
```

## Steps

### Phase 1 — Plan (always first)

1. Ask clarifying questions if requirements are ambiguous (max 3 questions)
2. Enter Plan mode and produce:
   - What changes (files, APIs, DB schema, UI)
   - How it will be tested
   - Which areas are off-limits or need approval
3. Present the plan and wait for approval before writing any code

### Phase 2 — Build

Dispatch sub-agents based on what the feature touches:

| Area                 | Agent            |
| -------------------- | ---------------- |
| API / backend logic  | `backend-agent`  |
| UI / components      | `frontend-agent` |
| Research / decisions | `researcher`     |

Each sub-agent should:

1. Write tests first (TDD)
2. Implement the feature
3. Run `npm test` and `npm run typecheck` before returning

### Phase 3 — Integration

1. Collect outputs from all sub-agents
2. Verify the full feature works end-to-end
3. Run `/security-check` if the feature touches auth, payments, or user data
4. Commit with message: `feat(<scope>): <description>`

## Rules

- Never build before the plan is approved
- Never skip tests
- Off-limits areas (`/src/auth/**`, `/src/payments/**`) require explicit approval even in planning
