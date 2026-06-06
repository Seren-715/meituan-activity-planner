# Writing Implementation Plans

## Core Principle
A good plan makes implementation obvious. If someone has to guess, the plan is incomplete.

## Bite-Sized Tasks
Each task = 2-5 minutes of focused work:
- "Write the failing test" — step
- "Run it to make sure it fails" — step
- "Implement minimal code to pass" — step
- "Run tests to verify" — step
- "Commit" — step

## Plan Document Structure

```markdown
# [Feature Name] Implementation Plan

**Goal:** [One sentence describing what this builds]
**Architecture:** [2-3 sentences about approach]
**Tech Stack:** [Key technologies/libraries]

---

### Task N: [Descriptive Name]

**Objective:** [One sentence]

**Files:**
- Create: `path/to/new_file.py`
- Modify: `path/to/existing.py:45-67`
- Test: `path/to/test_file.py`

**Step 1: Write failing test** (include code)
**Step 2: Run to verify failure** (exact command + expected output)
**Step 3: Write minimal implementation** (include code)
**Step 4: Run to verify pass** (exact command + expected output)
**Step 5: Commit** (exact commands)
```

## Principles
- **DRY** — Don't Repeat Yourself. Extract shared logic.
- **YAGNI** — You Aren't Gonna Need It. Only implement what's needed now.
- **TDD** — Test first, code second.
- **Frequent Commits** — Commit after every task.

## Common Mistakes
- Vague tasks ("Add authentication" → "Create User model with email field")
- Incomplete code (include the actual code, not "add validation function")
- Missing verification steps
- Missing exact file paths
