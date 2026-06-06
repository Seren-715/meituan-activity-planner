# Code Review Checklist

## Correctness
- Does the code do what it claims?
- Edge cases handled (empty inputs, nulls, large data, concurrent access)?
- Error paths handled gracefully?

## Security
- No hardcoded secrets, credentials, or API keys
- Input validation on user-facing inputs
- No SQL injection, XSS, or path traversal
- Auth/authz checks where needed

## Code Quality
- Clear naming (variables, functions, classes)
- No unnecessary complexity or premature abstraction
- DRY — no duplicated logic that should be extracted
- Functions have single responsibility
- No debug statements, TODOs, FIXMEs left behind
- No merge conflict markers

## Testing
- New code paths tested?
- Happy path and error cases covered?
- Tests readable and maintainable?

## Performance
- No N+1 queries or unnecessary loops
- Appropriate caching where beneficial
- No blocking operations in async code paths

## Documentation
- Public APIs documented
- Non-obvious logic has comments explaining "why"
- README updated if behavior changed

## Review Output Format
```
## Code Review Summary

### Critical
- **file:line** — Issue description. Suggestion.

### Warnings
- **file:line** — Issue description.

### Suggestions
- **file:line** — Improvement suggestion.

### Looks Good
- What's working well
```

## Reviewing a PR
```bash
git fetch origin pull/123/head:pr-123
git checkout pr-123
git diff main...pr-123           # Full diff
git diff main...pr-123 --stat    # Changed files summary
git diff main...pr-123 -- path/to/file.py  # Per-file diff

# Check for common issues
git diff main...HEAD | grep -n "print(\|console\.log\|TODO\|FIXME\|debugger"
git diff main...HEAD | grep -in "password\|secret\|api_key\|token.*="
git diff main...HEAD | grep -n "<<<<<<\|>>>>>>\|======="

gh pr review 123 --approve --body "LGTM!"
gh pr review 123 --request-changes --body "See inline comments."
```
