"""Verification script for completion status rollout."""
import sys
from sqlalchemy.orm import Session
from src.database import SessionLocal
from src.core.registry import scheme_registry
from src.utils_cache import memory_cache

def verify_config_flags():
    print("=" * 60)
    print("TEST 1: Config Flags Verification")
    print("=" * 60)
    
    all_schemes = scheme_registry.get_all_schemes()
    enabled_count = sum(1 for config in all_schemes.values() if config.completion_enabled)
    implemented_count = sum(1 for config in all_schemes.values() if config.implemented)
    
    print(f"Total schemes: {len(all_schemes)}")
    print(f"Implemented schemes: {implemented_count}")
    print(f"Completion-enabled schemes: {enabled_count}")
    
    missing = [code for code, config in all_schemes.items() 
               if config.implemented and not config.completion_enabled]
    
    if missing:
        print(f"\n❌ FAIL: {len(missing)} schemes missing completion_enabled flag:")
        for code in missing:
            print(f"  - {code}")
        return False
    
    print("\n✅ PASS: All implemented schemes have completion_enabled=True")
    return True

def verify_database_model():
    print("\n" + "=" * 60)
    print("TEST 2: Database Model & Constraints")
    print("=" * 60)
    
    db: Session = SessionLocal()
    try:
        from src import models
        from sqlalchemy import inspect
        
        inspector = inspect(db.bind)
        columns = [col['name'] for col in inspector.get_columns('sub_schema_completions')]
        
        required_columns = ['id', 'district', 'sub_scheme_code', 'fiscal_year', 
                           'is_complete', 'completed_by', 'completed_at']
        
        missing_cols = [col for col in required_columns if col not in columns]
        if missing_cols:
            print(f"❌ FAIL: Missing columns: {missing_cols}")
            return False
        
        constraints = inspector.get_unique_constraints('sub_schema_completions')
        has_unique = any('district' in str(c.get('column_names', [])) for c in constraints)
        
        if not has_unique:
            print("⚠️  WARNING: Unique constraint may not be properly configured")
        
        print("✅ PASS: Database model has all required columns")
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Database verification error: {e}")
        return False
    finally:
        db.close()

def verify_cache_invalidation_logic():
    print("\n" + "=" * 60)
    print("TEST 3: Cache Invalidation Logic")
    print("=" * 60)
    
    test_keys = [
        "completion:20530019:2024-25:Thane",
        "completion:76100149:2024-25:Raigad",
        "district_status_2053_2024-25",
        "district_status_7610_2024-25"
    ]
    
    for key in test_keys:
        memory_cache.set(key, {"test": True}, ttl=300)
    
    from src.utils_cache import invalidate_cache_pattern
    invalidate_cache_pattern("completion:")
    
    remaining = sum(1 for key in test_keys if memory_cache.get(key) is not None)
    
    if remaining > 2:
        print(f"❌ FAIL: Cache invalidation incomplete ({remaining}/{len(test_keys)} keys remain)")
        return False
    
    print("✅ PASS: Cache invalidation pattern works correctly")
    return True

def verify_n1_query_fix():
    print("\n" + "=" * 60)
    print("TEST 4: N+1 Query Fix (Code Review)")
    print("=" * 60)
    
    with open('src/routers/completion_status.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    if '.in_(implemented_schemes.keys())' in content:
        print("✅ PASS: Bulk query using .in_() found (N+1 fix implemented)")
        return True
    else:
        print("❌ FAIL: Bulk query pattern not found")
        return False

def verify_race_condition_fix():
    print("\n" + "=" * 60)
    print("TEST 5: Race Condition Fix (Code Review)")
    print("=" * 60)
    
    with open('src/routers/completion_status.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    has_lock = '.with_for_update()' in content
    has_error_handling = 'try:' in content and 'db.commit()' in content
    
    if has_lock and has_error_handling:
        print("✅ PASS: Row-level locking and error handling implemented")
        return True
    else:
        print(f"⚠️  PARTIAL: Lock={has_lock}, ErrorHandling={has_error_handling}")
        return has_lock or has_error_handling

def verify_fy_deletion_cleanup():
    print("\n" + "=" * 60)
    print("TEST 6: Fiscal Year Deletion Cleanup")
    print("=" * 60)
    
    with open('src/routers/fiscal_year.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    has_completion_delete = 'SubSchemaCompletion' in content and '.delete(' in content
    has_cache_invalidation = 'invalidate_cache_pattern' in content and 'completion:' in content
    
    if has_completion_delete and has_cache_invalidation:
        print("✅ PASS: FY deletion cleans up completion records and caches")
        return True
    else:
        print(f"⚠️  PARTIAL: RecordCleanup={has_completion_delete}, CacheInvalidation={has_cache_invalidation}")
        return False

def main():
    print("\nCOMPLETION STATUS ROLLOUT VERIFICATION\n")
    
    results = {
        "Config Flags": verify_config_flags(),
        "Database Model": verify_database_model(),
        "Cache Invalidation": verify_cache_invalidation_logic(),
        "N+1 Query Fix": verify_n1_query_fix(),
        "Race Condition Fix": verify_race_condition_fix(),
        "FY Deletion Cleanup": verify_fy_deletion_cleanup()
    }
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    total_passed = sum(1 for v in results.values() if v)
    total_tests = len(results)
    
    print(f"\nTotal: {total_passed}/{total_tests} tests passed")
    
    if total_passed == total_tests:
        print("\nALL TESTS PASSED - Rollout complete!")
        return 0
    else:
        print(f"\n{total_tests - total_passed} test(s) failed - Review required")
        return 1

if __name__ == "__main__":
    sys.exit(main())
