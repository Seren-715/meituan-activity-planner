# Test-Driven Development (TDD) Workflow

## Iron Law
NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST

## Red-Green-Refactor Cycle

### RED — Write Failing Test
- One behavior per test
- Clear descriptive name (if "and" in name → split it)
- Test real behavior, not mocks
- Name describes behavior, not implementation

### Verify RED — Watch It Fail (MANDATORY)
```bash
pytest tests/test_feature.py::test_name -v
```
Confirm: test fails for expected reason (feature missing), not typos.

### GREEN — Minimal Code
- Write simplest code to pass the test
- Nothing more (no logging, no extra features)
- Cheating is OK: hardcode, copy-paste, duplicate — fix in REFACTOR

### Verify GREEN — Watch It Pass
```bash
pytest tests/test_feature.py::test_name -v
pytest tests/ -q   # Full suite for regressions
```

### REFACTOR — Clean Up
- Remove duplication, improve names, extract helpers
- Keep tests green throughout
- If tests fail → undo, take smaller steps

## Why Order Matters
- Tests written after code pass immediately → proves nothing
- Test-first forces you to see failure → proves test actually works
- Manual testing is ad-hoc, not systematic

## Red Flags — START OVER
- Code before test / Test after implementation
- Test passes immediately on first run
- "Keep as reference" / "adapt existing code"
- Rationalizing "just this once"

## Anti-Patterns
- Testing mock behavior instead of real behavior
- Testing implementation details
- Happy path only — always test edge cases
- Brittle tests tied to structure, not behavior
