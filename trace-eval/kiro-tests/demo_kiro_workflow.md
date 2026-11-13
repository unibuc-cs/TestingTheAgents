# Kiro Spec-Driven Development Workflow Demo

This document walks through the complete Kiro workflow, demonstrating how spec-driven development with property-based testing works end-to-end.

---

## Feature Request (Natural Language)

**User prompt:**

> "I need a function that calculates the discount for a product. The discount percentage should be between 0 and 100. The function should return the final price after applying the discount. If the discount is invalid, it should raise an error."

---

## Phase 1: Requirements Extraction

Kiro would analyze this and extract structured requirements:

### Requirement 1: Discount validation
The discount percentage MUST be a number between 0 and 100 (inclusive).

**Acceptance criteria:**
- GIVEN a discount percentage
- WHEN it is less than 0 OR greater than 100
- THEN the function SHALL raise a ValueError

### Requirement 2: Price calculation
The function MUST calculate the final price correctly using the formula:
`final_price = original_price * (1 - discount / 100)`

**Acceptance criteria:**
- GIVEN an original price and valid discount
- WHEN the function is called
- THEN the result SHALL equal `original_price * (1 - discount / 100)`

### Requirement 3: Non-negative prices
The original price MUST be non-negative.

**Acceptance criteria:**
- GIVEN a negative original price
- WHEN the function is called
- THEN the function SHALL raise a ValueError

---

## Phase 2: Design

### Function Signature
```python
def calculate_discounted_price(original_price: float, discount_percent: float) -> float:
    """
    Calculate the final price after applying a discount.
    
    Args:
        original_price: The original price (must be >= 0)
        discount_percent: The discount percentage (must be 0-100)
        
    Returns:
        The final price after discount
        
    Raises:
        ValueError: If inputs are invalid
    """
```

### Properties Extracted (for PBT)

Kiro would identify these properties during design:

1. **Property: Discount bounds**
   - For any original_price >= 0 and discount in [0, 100], the function succeeds
   - For any discount < 0 or > 100, the function raises ValueError

2. **Property: Correct calculation**
   - For all valid inputs, result == original_price * (1 - discount / 100)

3. **Property: Price never negative**
   - For all valid inputs, result >= 0

4. **Property: Edge cases**
   - discount = 0 → result == original_price
   - discount = 100 → result == 0

---

## Phase 3: Tasks

Kiro breaks this into tasks:

- [ ] Task 1: Implement `calculate_discounted_price` function
- [ ] Task 2: Add input validation
- [ ] Task 3: Generate and run property-based tests

---

## Phase 4: Implementation

*Kiro would implement this. I'll do it manually to show the complete flow.*

---

## Phase 5: Property-Based Testing

*This is where Kiro's PBT feature activates. I'll generate the tests.*

---

*Continue reading below to see each phase executed...*
