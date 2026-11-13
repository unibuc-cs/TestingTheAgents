"""Demonstration of PBT finding a bug through shrinking.

This shows what happens when the implementation violates the spec.
We'll simulate a buggy retry implementation that regenerates the key on every attempt.
"""

from hypothesis import given, strategies as st, settings
from traceeval.sut.services.errors import TransientError
import uuid


# --- BUGGY IMPLEMENTATION: regenerates key on each retry ---

def buggy_with_retry(call, *, retries: int, is_write: bool, idempotency_enabled: bool):
    """
    BUG: This generates a NEW idempotency key on EVERY attempt instead of reusing one.
    This violates FS-0105: 'A write is retried with THE SAME key.'
    """
    attempt = 0
    while True:
        attempt += 1
        
        # BUG: Key is generated inside the loop
        key = f"idem-{uuid.uuid4().hex[:10]}" if (is_write and idempotency_enabled) else None
        
        try:
            result = call(key)
            return result, attempt, key
        except TransientError:
            if attempt > retries:
                raise


# --- Property test that will FAIL and show shrinking ---

@given(
    retries=st.integers(min_value=1, max_value=10),
    fail_count=st.integers(min_value=1, max_value=20),
)
@settings(max_examples=100)
def test_buggy_implementation_violates_key_stability(retries, fail_count):
    """
    This will FAIL because buggy_with_retry generates a new key on every attempt.
    
    Hypothesis will:
    1. Find a failing case (e.g., retries=7, fail_count=13)
    2. Shrink it to the MINIMAL failing case (e.g., retries=1, fail_count=1)
    3. Report the smallest example that demonstrates the bug
    """
    seen_keys = []
    attempt_count = [0]
    
    def mock_call(idempotency_key):
        attempt_count[0] += 1
        seen_keys.append(idempotency_key)
        
        if attempt_count[0] <= fail_count:
            raise TransientError("Simulated failure")
        
        return {"status": "success"}
    
    try:
        result, attempts, final_key = buggy_with_retry(
            mock_call,
            retries=retries,
            is_write=True,
            idempotency_enabled=True
        )
        
        # This assertion will FAIL when there's more than one attempt
        assert len(set(seen_keys)) == 1, (
            f"BUG FOUND: Keys changed across retries!\n"
            f"  Attempts: {attempts}\n"
            f"  Keys seen: {seen_keys}\n"
            f"  Unique keys: {len(set(seen_keys))}\n"
            f"  Test params: retries={retries}, fail_count={fail_count}"
        )
        
    except TransientError:
        # Even on failure, check if keys were stable
        if len(seen_keys) > 1:
            assert len(set(seen_keys)) == 1, (
                f"BUG FOUND: Keys changed even in failed attempts!\n"
                f"  Keys seen: {seen_keys}"
            )


if __name__ == "__main__":
    import pytest
    import sys
    
    print("=" * 70)
    print("DEMONSTRATING PROPERTY-BASED TESTING WITH SHRINKING")
    print("=" * 70)
    print()
    print("This test will:")
    print("1. Generate random (retries, fail_count) pairs")
    print("2. Find cases where the buggy code violates key stability")
    print("3. SHRINK the failing case to the minimal reproducing example")
    print()
    print("Watch for Hypothesis to report the SHRUNK example!")
    print("=" * 70)
    print()
    
    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))
