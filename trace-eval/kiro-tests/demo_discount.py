"""
Demo: Discount calculation function
Created following Kiro spec-driven workflow
"""


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
        
    Properties (verified by PBT):
        - For discount in [0, 100] and price >= 0, returns valid result
        - result == original_price * (1 - discount_percent / 100)
        - result >= 0 for all valid inputs
        - discount = 0 → result == original_price
        - discount = 100 → result == 0
    """
    # Validation
    if original_price < 0:
        raise ValueError(f"Original price must be non-negative, got {original_price}")
    
    if not (0 <= discount_percent <= 100):
        raise ValueError(f"Discount must be between 0 and 100, got {discount_percent}")
    
    # Calculation
    final_price = original_price * (1 - discount_percent / 100)
    
    return final_price
