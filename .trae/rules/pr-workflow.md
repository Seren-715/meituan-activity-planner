# GitHub Pull Request Workflow

## Branch Creation
```bash
git fetch origin
git checkout main && git pull origin main
git checkout -b feat/description   # or fix/, refactor/, docs/, ci/
```

## Conventional Commits
```
type(scope): short description

Longer explanation if needed. Wrap at 72 chars.
```
Types: `feat`, `fix`, `refactor`, `docs`, `test`, `ci`, `chore`, `perf`

## Push and Create PR
```bash
git push -u origin HEAD
gh pr create --title "type: description" --body "## Summary\n- What changed\n\n## Test Plan\n- Tests pass"
```

## Monitoring CI
```bash
gh pr checks           # one-shot check
gh pr checks --watch   # poll until done
```

## Auto-Fix CI Failures Loop
1. Check CI status → identify failures
2. Read failure logs → understand the error
3. Fix the code
4. `git add . && git commit -m "fix: ..." && git push`
5. Wait for CI → re-check
6. Repeat up to 3 attempts, then ask for help

## Merging
```bash
gh pr merge --squash --delete-branch
```

## Complete Workflow
```bash
# 1. Start from main
git checkout main && git pull origin main

# 2. Branch
git checkout -b fix/login-redirect-bug

# 3. Make changes (TDD: test first!)

# 4. Commit
git add src/auth/login.py tests/test_login.py
git commit -m "fix: correct redirect URL after login"

# 5. Push
git push -u origin HEAD

# 6. Create PR → Monitor CI → Merge
```
