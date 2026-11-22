"""Property-based test for FS-0105: Idempotent retries.

This demonstrates how PBT works for the spec requirement:
'A write is always retried with the same idempotency key across all attempts.'
"""

from hypothesis import given, strategies as st, settings, example
from traceeval.sut.harness.retry import with_retry
from traceeval.sut.services.errors import TransientError


# --- Property 1: Same key across all retry attempts ---

@given(
    retries=st.integers(min_value=1, max_value=5),
    fail_count=st.integers(min_value=0, max_value=10),
)
@settings(max_examples=500)  # Generate 500 random test cases
@example(retries=3, fail_count=3)  # Explicit example: exactly at the retry limit
@example(retries=1, fail_count=5)  # Explicit example: exceeds retry limit
def test_write_always_uses_same_idempotency_key(retries, fail_count):
    """
    Property: For any write call that is retried, the idempotency key passed
    to the call function is identical across all attempts.
    
    This tests FS-0105 Requirement: "Every write tool MUST carry an idempotency key"
    and the key must be stable across retries.
    """
    seen_keys = []
    attempt_count = [0]
    
    def mock_call(idempotency_key):
        """Mock tool that fails fail_count times, then succeeds."""
        attempt_count[0] += 1
        seen_keys.append(idempotency_key)
        
        if attempt_count[0] <= fail_count:
            raise TransientError("Simulated transient failure")
        
        return {"status": "success", "data": "result"}
    
    # Run with_retry as a write operation with idempotency enabled
    try:
        result, attempts, key = with_retry(
            mock_call,
            retries=retries,
            is_write=True,
            idempotency_enabled=True
        )
        
        # Property 1: All keys seen must be identical
        assert len(set(seen_keys)) == 1, \
            f"Keys differed across attempts: {seen_keys}"
        
        # Property 2: The returned key must match what was used
        assert key == seen_keys[0], \
            f"Returned key {key} != used key {seen_keys[0]}"
        
        # Property 3: Key must not be None for writes
        assert key is not None, \
            "Write operation returned None as idempotency key"
        
    except TransientError:
        # If we exhausted retries, still check key consistency
        if seen_keys:
            assert len(set(seen_keys)) == 1, \
                f"Keys differed even in failed attempts: {seen_keys}"


# --- Property 2: Reads never get an idempotency key ---

@given(
    retries=st.integers(min_value=1, max_value=5),
    fail_count=st.integers(min_value=0, max_value=3),
)
@settings(max_examples=300)
def test_read_never_gets_idempotency_key(retries, fail_count):
    """
    Property: Read operations (is_write=False) never receive an idempotency key,
    regardless of the idempotency_enabled setting.
    
    This is an implicit constraint from the spec: only writes need keys.
    """
    seen_keys = []
    attempt_count = [0]
    
    def mock_call(idempotency_key):
        attempt_count[0] += 1
        seen_keys.append(idempotency_key)
        
        if attempt_count[0] <= fail_count:
            raise TransientError("Simulated transient failure")
        
        return {"status": "success"}
    
    try:
        result, attempts, key = with_retry(
            mock_call,
            retries=retries,
            is_write=False,  # This is a READ
            idempotency_enabled=True
        )
        
        # Property: All keys must be None for reads
        assert all(k is None for k in seen_keys), \
            f"Read operation received non-None keys: {seen_keys}"
        
        assert key is None, \
            f"Read operation returned non-None key: {key}"
        
    except TransientError:
        # Even on failure, reads should never see keys
        assert all(k is None for k in seen_keys), \
            f"Read operation received non-None keys on failure: {seen_keys}"


# --- Property 3: Idempotency disabled means no keys ---

@given(
    retries=st.integers(min_value=1, max_value=5),
)
@settings(max_examples=200)
def test_write_without_idempotency_gets_no_key(retries):
    """
    Property: When idempotency_enabled=False, even write operations
    receive no key (simulating the feature being turned off).
    """
    seen_keys = []
    
    def mock_call(idempotency_key):
        seen_keys.append(idempotency_key)
        return {"status": "success"}
    
    result, attempts, key = with_retry(
        mock_call,
        retries=retries,
        is_write=True,
        idempotency_enabled=False  # Feature disabled
    )
    
    # Property: No keys should be generated
    assert all(k is None for k in seen_keys)
    assert key is None


# --- Property 4: Shrinking demonstration ---

@given(
    retries=st.integers(min_value=1, max_value=100),
    attempts_before_success=st.integers(min_value=0, max_value=200),
)
@settings(max_examples=1000)
def test_retry_budget_is_respected(retries, attempts_before_success):
    """
    Property: If a call fails more times than the retry budget allows,
    the final TransientError is raised, and the total attempts equals retries + 1.
    
    This will find the boundary case and shrink it to the minimal failing example.
    """
    attempt_count = [0]
    
    def mock_call(idempotency_key):
        attempt_count[0] += 1
        if attempt_count[0] <= attempts_before_success:
            raise TransientError("Still failing")
        return "success"
    
    if attempts_before_success > retries:
        # Should exhaust retries
        try:
            with_retry(mock_call, retries=retries, is_write=True, idempotency_enabled=True)
            assert False, "Should have raised TransientError"
        except TransientError:
            # Property: attempts should be exactly retries + 1
            assert attempt_count[0] == retries + 1, \
                f"Expected {retries + 1} attempts, got {attempt_count[0]}"
    else:
        # Should succeed
        result, attempts, key = with_retry(
            mock_call, retries=retries, is_write=True, idempotency_enabled=True
        )
        assert attempts == attempts_before_success + 1


if __name__ == "__main__":
    import pytest
    import sys
    
    # Run with pytest for better output
    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))
