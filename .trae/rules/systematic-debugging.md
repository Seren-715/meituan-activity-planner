# Systematic Debugging — 4-Phase Root Cause Analysis

## Iron Law
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST

## Phase 1: Root Cause Investigation
BEFORE attempting ANY fix:

1. **Read Error Messages Carefully** — line numbers, file paths, error codes
2. **Reproduce Consistently** — can you trigger it reliably every time?
3. **Check Recent Changes** — `git log --oneline -10`, `git diff`, recent deps
4. **Gather Evidence** — for multi-component systems: log data at each boundary
5. **Trace Data Flow** — where does the bad value originate? Fix at source, not symptom

**Phase 1 Complete when:** You understand WHY it's happening.

## Phase 2: Pattern Analysis
1. Find working examples in the same codebase
2. Compare against references — read completely, don't skim
3. Identify every difference between working and broken
4. Understand dependencies, config, assumptions

## Phase 3: Hypothesis and Testing
1. Form single hypothesis: "I think X is root cause because Y"
2. Make the SMALLEST possible change to test it
3. One variable at a time
4. Verify before continuing

## Phase 4: Implementation
1. Create failing test case reproducing the bug
2. One fix only — address root cause, not symptom
3. Verify fix + full suite for regressions

**Rule of Three:** If 3+ fixes failed → STOP and question the architecture.
Don't attempt Fix #4 without architectural discussion.

## Red Flags
- "Quick fix for now, investigate later"
- "Just try changing X and see if it works"
- "Multiple changes at once saves time"
- "I don't fully understand but this might work"
