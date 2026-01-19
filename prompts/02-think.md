# Think Before Code

How a senior developer thinks before implementing any feature.

## Step 1: Understand
Ask yourself:
- What exactly is being requested?
- What problem does this solve?
- What are the inputs and outputs?
- What are the edge cases?

## Step 2: Explore
Before writing anything:
- Search codebase for similar features
- Find existing patterns to follow
- Identify utilities to reuse
- Check for related tests

## Step 3: Design
Plan the minimal solution:
- Where does this code belong?
- What existing code needs modification?
- What new code is actually needed?
- How do errors propagate?

## Step 4: Validate
Before coding, confirm:
- Simplest approach chosen?
- Follows existing architecture?
- No unnecessary new files?
- Error cases covered?

## Thinking by Task Type

### New Feature
```
1. Find similar feature in codebase
2. Copy pattern, adapt to need
3. Reuse existing services/utils
4. Add to existing structure
```

### Bug Fix
```
1. Reproduce the issue
2. Trace the data flow
3. Find root cause (not symptom)
4. Minimal fix at source
```

### Refactor
```
1. Ensure tests exist first
2. One change at a time
3. Verify behavior unchanged
4. Commit after each step
```

## Red Flags (Stop & Rethink)
- Creating many new files
- Solution feels complex
- Duplicating existing logic
- Unsure where code belongs
