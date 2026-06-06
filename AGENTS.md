# Trae AI Coding Rules

This file defines the development conventions and workflows for AI coding assistants in this project.

## Core Workflows

### 1. Test-Driven Development (TDD)
Follow RED-GREEN-REFACTOR cycle:
- **RED**: Write failing test first
- **Verify**: Watch it fail (MANDATORY — proves test works)
- **GREEN**: Write minimal code to pass
- **Verify**: Watch it pass + full suite
- **REFACTOR**: Clean up, keep tests green

**Iron Law:** NO production code without a failing test first. Test-after code must be deleted and rewritten.

### 2. Systematic Debugging
4-phase root cause analysis:
1. **Investigate** — Read errors, reproduce, check history, trace data flow
2. **Pattern** — Find working examples, compare, identify differences
3. **Hypothesis** — Single theory, minimal test, one variable at a time
4. **Implement** — Regression test first, one fix, verify

**Rule of Three:** After 3 failed fixes → STOP. Question the architecture.

### 3. Pre-Commit Verification
Before every commit:
- Security scan (secrets, injection, eval/exec)
- Run tests + linting
- Self-review checklist
- Fix issues before committing

### 4. PR Workflow
```bash
git checkout -b type/description   # branch
git commit -m "type(scope): msg"   # conventional commits
git push -u origin HEAD
gh pr create                        # create PR
gh pr merge --squash --delete-branch  # merge
```

## Code Quality Standards

### Security (Critical)
- Parameterized SQL queries only — no string interpolation
- No hardcoded secrets, API keys, or credentials
- Validate all user inputs
- Use `subprocess.run()` with list args, not `os.system()` or `shell=True`
- Sanitize file paths to prevent traversal

### Code Style
- Clear, descriptive names for variables, functions, classes
- Single responsibility per function
- DRY — extract shared logic
- Comments explain "why", not "what" (code already shows "what")
- No debug print/console.log in committed code

### Testing
- Every new function/method needs a test
- Cover happy path AND error cases/edge cases
- Tests should be readable and maintainable
- Use real code over mocks when possible

## Project File Structure
(To be filled per project)

## Commit Conventions
Use conventional commits:
- `feat:` — new feature
- `fix:` — bug fix
- `refactor:` — code restructuring
- `docs:` — documentation
- `test:` — testing
- `ci:` — CI/CD changes
- `chore:` — maintenance
