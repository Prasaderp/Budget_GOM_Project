# Implementation Rules

How to write code like a senior developer.

## Code Structure
Every function follows this pattern:
```
def function_name(params):
    # 1. Validate inputs (fail fast)
    if not valid:
        raise Error("clear message")
    
    # 2. Handle edge cases
    if edge_case:
        return early
    
    # 3. Core logic (minimal)
    result = do_work()
    
    # 4. Return/cleanup
    return result
```

## Naming
- Functions: `verb_noun` → `get_user`, `validate_input`
- Variables: descriptive → `user_count`, not `uc`
- Booleans: `is_`, `has_`, `can_` → `is_valid`
- Constants: `UPPER_SNAKE` → `MAX_RETRIES`

## Error Handling
```
# Good: Specific, contextual
raise ValueError(f"User {user_id} not found in {table}")

# Bad: Generic
raise Exception("Error")
```

## Patterns to Follow
| Situation | Pattern |
|-----------|---------|
| Repeated code | Extract function |
| Deep nesting | Early return |
| Many params | Use object/dict |
| Complex condition | Extract to named variable |
| Magic value | Named constant |

## Anti-Patterns to Avoid
| Bad | Fix |
|-----|-----|
| God function (>20 lines) | Split into helpers |
| Copy-paste code | Extract shared function |
| Deep nesting (>3) | Guard clauses |
| Commented code | Delete it |
| TODO in production | Complete it |

## Self-Check Before Commit
- Can this be shorter?
- Would I understand this in 6 months?
- Are all errors handled?
- Did I follow codebase patterns?
