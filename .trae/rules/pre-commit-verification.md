# Pre-Commit Code Verification Pipeline

## Step 1: Get the Diff
```bash
git diff --cached   # staged changes
git diff            # unstaged changes
```

## Step 2: Static Security Scan
Scan added lines for:
- Hardcoded secrets/API keys/tokens
- Shell injection (`os.system()`, `subprocess shell=True`)
- Dangerous eval/exec
- Unsafe deserialization (pickle)
- SQL injection (string formatting in queries)

## Step 3: Run Tests & Linting
```bash
# Python
pytest --tb=no -q   # run tests
ruff check .        # lint
mypy .              # type check

# Node
npm test
npx eslint .
npx tsc --noEmit
```

## Step 4: Self-Review Checklist
- [ ] No hardcoded secrets, API keys, or credentials
- [ ] Input validation on user-provided data
- [ ] SQL queries use parameterized statements
- [ ] File operations validate paths
- [ ] External calls have error handling
- [ ] No debug print/console.log left behind
- [ ] No commented-out code
- [ ] New code has tests

## Step 5: Commit
```bash
git add -A && git commit -m "type(scope): description"
```

## Common Security Issues

### Python
```python
# BAD: SQL injection
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
# GOOD: parameterized
cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))

# BAD: shell injection
os.system(f"ls {user_input}")
# GOOD: safe subprocess
subprocess.run(["ls", user_input], check=True)
```

### JavaScript
```javascript
// BAD: XSS
element.innerHTML = userInput;
// GOOD: safe
element.textContent = userInput;
```
