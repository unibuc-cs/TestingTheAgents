"""
Property-based tests for discount calculation
Auto-generated following Kiro PBT workflow
"""

from hypothesis import given, strategies as st, settings, example, assume
import pytest
import math
from demo_discount import calculate_discounted_price


# ============================================================================
# Property 1: Valid inputs always succeed
# ============================================================================

@given(
    original_price=st.floats(min_value=0, max_value=1_000_000, allow_nan=False, allow_infinity=False),
    discount_percent=st.floats(min_value=0, max_value=100, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=500)
@example(original_price=0.0, discount_percent=0.0)  # Edge: zero price
@example(original_price=100.0, discount_percent=100.0)  # Edge: full discount
@example(original_price=99.99, discount_percent=50.0)  # Common case
def test_valid_inputs_succeed(original_price, discount_percent):
    """
    Property: For any price >= 0 and discount in [0, 100],
    the function returns a valid result without raising an error.
    """
    result = calculate_discounted_price(original_price, discount_percent)
    
    # Result should be a number
    assert isinstance(result, float)
    assert not math.isnan(result)
    assert not math.isinf(result)


# ============================================================================
# Property 2: Correct calculation formula
# ============================================================================

@given(
    original_price=st.floats(min_value=0, max_value=1_000_000, allow_nan=False, allow_infinity=False),
    discount_percent=st.floats(min_value=0, max_value=100, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=1000)
@example(original_price=100.0, discount_percent=25.0)  # Should be 75.0
@example(original_price=50.0, discount_percent=10.0)   # Should be 45.0
def test_calculation_formula(original_price, discount_percent):
    """
    Property: result == original_price * (1 - discount_percent / 100)
    
    This is the core correctness property: the math must be exact.
    """
    result = calculate_discounted_price(original_price, discount_percent)
    expected = original_price * (1 - discount_percent / 100)
    
    # Use relative tolerance for floating point comparison
    assert math.isclose(result, expected, rel_tol=1e-9), \
        f"Expected {expected}, got {result}"


# ============================================================================
# Property 3: Result is never negative
# ============================================================================

@given(
    original_price=st.floats(min_value=0, max_value=1_000_000, allow_nan=False, allow_infinity=False),
    discount_percent=st.floats(min_value=0, max_value=100, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=500)
def test_result_never_negative(original_price, discount_percent):
    """
    Property: For all valid inputs, the result is >= 0.
    
    A negative price would be nonsensical in any business context.
    """
    result = calculate_discounted_price(original_price, discount_percent)
    assert result >= 0, f"Result was negative: {result}"


# ============================================================================
# Property 4: Edge case - zero discount returns original price
# ============================================================================

@given(
    original_price=st.floats(min_value=0, max_value=1_000_000, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=300)
@example(original_price=42.0)
def test_zero_discount_returns_original(original_price):
    """
    Property: discount = 0 → result == original_price
    
    No discount means no change in price.
    """
    result = calculate_discounted_price(original_price, 0.0)
    assert math.isclose(result, original_price, rel_tol=1e-9)


# ============================================================================
# Property 5: Edge case - 100% discount returns zero
# ============================================================================

@given(
    original_price=st.floats(min_value=0, max_value=1_000_000, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=300)
@example(original_price=199.99)
def test_full_discount_returns_zero(original_price):
    """
    Property: discount = 100 → result == 0
    
    A 100% discount means the item is free.
    """
    result = calculate_discounted_price(original_price, 100.0)
    assert math.isclose(result, 0.0, abs_tol=1e-9)


# ============================================================================
# Property 6: Invalid discount < 0 raises ValueError
# ============================================================================

@given(
    original_price=st.floats(min_value=0, max_value=1_000_000, allow_nan=False, allow_infinity=False),
    discount_percent=st.floats(max_value=-0.01, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=200)
@example(original_price=100.0, discount_percent=-1.0)
@example(original_price=50.0, discount_percent=-100.0)
def test_negative_discount_raises_error(original_price, discount_percent):
    """
    Property: For any discount < 0, ValueError is raised.
    
    Negative discounts don't make business sense.
    """
    with pytest.raises(ValueError, match="Discount must be between 0 and 100"):
        calculate_discounted_price(original_price, discount_percent)


# ============================================================================
# Property 7: Invalid discount > 100 raises ValueError
# ============================================================================

@given(
    original_price=st.floats(min_value=0, max_value=1_000_000, allow_nan=False, allow_infinity=False),
    discount_percent=st.floats(min_value=100.01, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=200)
@example(original_price=100.0, discount_percent=101.0)
@example(original_price=50.0, discount_percent=500.0)
def test_excessive_discount_raises_error(original_price, discount_percent):
    """
    Property: For any discount > 100, ValueError is raised.
    
    You can't discount more than 100% of the price.
    """
    with pytest.raises(ValueError, match="Discount must be between 0 and 100"):
        calculate_discounted_price(original_price, discount_percent)


# ============================================================================
# Property 8: Negative price raises ValueError
# ============================================================================

@given(
    original_price=st.floats(max_value=-0.01, allow_nan=False, allow_infinity=False),
    discount_percent=st.floats(min_value=0, max_value=100, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=200)
@example(original_price=-1.0, discount_percent=50.0)
@example(original_price=-100.0, discount_percent=0.0)
def test_negative_price_raises_error(original_price, discount_percent):
    """
    Property: For any original_price < 0, ValueError is raised.
    
    Negative prices don't exist in normal commerce.
    """
    with pytest.raises(ValueError, match="Original price must be non-negative"):
        calculate_discounted_price(original_price, discount_percent)


# ============================================================================
# Property 9: Relationship - higher discount means lower price
# ============================================================================

@given(
    original_price=st.floats(min_value=1.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
    discount1=st.floats(min_value=0, max_value=99, allow_nan=False, allow_infinity=False),
    discount2=st.floats(min_value=0, max_value=99, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=500)
def test_higher_discount_means_lower_price(original_price, discount1, discount2):
    """
    Property: If discount_a > discount_b, then result_a < result_b
    
    Monotonicity property: more discount = less final price.
    """
    assume(discount1 != discount2)  # Skip equal cases
    
    result1 = calculate_discounted_price(original_price, discount1)
    result2 = calculate_discounted_price(original_price, discount2)
    
    if discount1 > discount2:
        assert result1 < result2 or math.isclose(result1, result2), \
            f"Higher discount should give lower price: {discount1}% → {result1}, {discount2}% → {result2}"
    else:
        assert result1 > result2 or math.isclose(result1, result2), \
            f"Lower discount should give higher price: {discount1}% → {result1}, {discount2}% → {result2}"


if __name__ == "__main__":
    # Run with pytest for best output
    import sys
    sys.exit(pytest.main([__file__, "-v", "--tb=short", "-s"]))
