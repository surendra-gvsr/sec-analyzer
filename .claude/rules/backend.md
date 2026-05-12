# Backend Rules

- Every API route must have rate limiting
- Always validate and sanitize input before touching any data
- Never use client-side database calls
- All secrets in .env only, never hardcode
- Use TypeScript strictly, no any types
- Always return consistent JSON response shape: {success, data, error}
- Parameterized queries only, no string concatenation in queries
