# Design Document: SEO Title Validation

## Overview

The SEO title validation feature provides a standalone validation function that checks SEO titles against platform constraints before they are applied to page metadata. The validation function is designed to be called early in the SEO title update workflow, enabling proper error handling and user feedback before any state modifications occur.

This design implements validation as a pure function that returns rich result objects, making it easy to test, reuse, and integrate into various workflows. The validation logic is colocated with the SEO service module for maintainability.

## Architecture

### Component Structure

The feature consists of a single validation function integrated into the existing SEO service:

```
traceeval/sut/services/seo.py
├── validate_seo_title()    # New validation function
├── get_seo_report()        # Existing SEO reporting
└── (other SEO functions)
```

### Validation Function Design

The `validate_seo_title` function is a pure function with no side effects:

**Input:**
- `title` (str | None): The title to validate
- `max_length` (int, optional): Maximum allowed length (defaults to reading from config)
- `config` (Config, optional): Configuration object for reading default max_length

**Output:**
- `dict`: A validation result containing status and detailed feedback

**Properties:**
- Pure function (no side effects, no state modification)
- Deterministic (same inputs always produce same outputs)
- Independently callable (no dependencies on other service functions)
- Fast execution (simple string length checks)

### Integration Points

1. **Configuration Service**: Reads `seo.max_title_length` from runtime configuration when max_length is not explicitly provided
2. **Repository Service**: Does NOT integrate with repository (validation occurs before any data access)
3. **SEO Service**: Can be called by other SEO service functions before applying metadata updates

## Data Models

### Validation Result Structure

The validation result is a dictionary with the following structure:

**Valid Result:**
```python
{
    "status": "valid",
    "length": int  # Length of the validated title
}
```

**Invalid Result (Empty Title):**
```python
{
    "status": "invalid",
    "reason": "empty_title"
}
```

**Invalid Result (Too Long):**
```python
{
    "status": "invalid",
    "reason": "too_long",
    "length": int,        # Actual length of the title
    "max_length": int     # Configured maximum length
}
```

### Validation Status Values

- `"valid"`: Title passes all validation checks
- `"invalid"`: Title fails one or more validation checks

### Validation Reason Values

- `"empty_title"`: Title is None or empty string
- `"too_long"`: Title length exceeds max_length

## Components and Interfaces

### Validation Function Component

The core component is the `validate_seo_title` function, which provides standalone validation functionality without dependencies on other service components.

**Responsibilities:**
- Validate title length constraints
- Check for empty/None titles
- Return structured validation results
- Read configuration when needed

**Dependencies:**
- `Config` class (optional, for reading default max_length)

**No dependencies on:**
- Repository service
- State objects
- Other SEO service functions

### Interface Specifications

#### validate_seo_title Function

```python
def validate_seo_title(
    title: str | None,
    max_length: int | None = None,
    config: Config | None = None
) -> dict:
    """Validate an SEO title against length constraints.
    
    Args:
        title: The title to validate (can be None or empty)
        max_length: Maximum allowed length. If None, reads from config.
        config: Configuration object for reading default max_length.
                If both max_length and config are None, defaults to 60.
    
    Returns:
        A validation result dictionary containing:
        - status: "valid" or "invalid"
        - length: Title length (for valid titles and too-long titles)
        - reason: Reason for rejection (for invalid titles)
        - max_length: Configured maximum (for too-long titles)
    
    Examples:
        >>> validate_seo_title("Valid Title", max_length=60)
        {"status": "valid", "length": 11}
        
        >>> validate_seo_title(None, max_length=60)
        {"status": "invalid", "reason": "empty_title"}
        
        >>> validate_seo_title("A" * 100, max_length=60)
        {"status": "invalid", "reason": "too_long", "length": 100, "max_length": 60}
    """
```

### Configuration Integration

The function reads configuration using this pattern:

```python
# Determine max_length
if max_length is None:
    if config is not None:
        max_length = config.get("seo.max_title_length", 60)
    else:
        max_length = 60  # Default fallback
```

This allows three usage patterns:
1. Explicit max_length: `validate_seo_title(title, max_length=60)`
2. Config-based: `validate_seo_title(title, config=cfg)`
3. Default: `validate_seo_title(title)` (uses 60 as fallback)

## Validation Logic

### Validation Steps

The validation function performs checks in this order:

1. **Empty Check**: If title is None or empty string → return invalid with "empty_title"
2. **Length Configuration**: Determine max_length from parameter or config
3. **Length Check**: If len(title) > max_length → return invalid with "too_long"
4. **Success**: Return valid with length information

### Validation Flowchart

```
title input
    ↓
Is title None or empty?
    ├─ Yes → {"status": "invalid", "reason": "empty_title"}
    └─ No
        ↓
    Determine max_length (from param, config, or default)
        ↓
    Is len(title) > max_length?
        ├─ Yes → {"status": "invalid", "reason": "too_long", "length": ..., "max_length": ...}
        └─ No → {"status": "valid", "length": ...}
```

### Edge Cases

1. **None title**: Treated as empty, returns "empty_title" reason
2. **Empty string**: Returns "empty_title" reason
3. **Whitespace-only title**: Currently treated as valid if within length limit (requirements don't specify trimming)
4. **Exactly max_length**: Valid (boundary is inclusive: 1 ≤ len ≤ max_length)
5. **Zero max_length**: Would make all non-empty titles invalid (unusual but handled correctly)
6. **Negative max_length**: Not explicitly handled (should be validated by caller)

## Error Handling

The validation function does NOT raise exceptions. All validation failures are returned as structured results with "invalid" status.

**Why no exceptions:**
- Validation failures are expected business logic, not exceptional conditions
- Returning structured results makes error handling easier for callers
- Enables better testing (no try/except needed)
- Consistent with validation function patterns

**Caller responsibility:**
- Check the "status" field in the result
- Handle invalid results appropriately (e.g., return error to user)
- Do not proceed with metadata updates if status is "invalid"

## Integration Workflow

### Before: Direct Metadata Update

```python
# Old workflow - no validation
def apply_seo_title(state, page_id, title, actor):
    return set_page_metadata(state, page_id, title=title, 
                           description=None, keywords=None, actor=actor)
```

### After: Validation First

```python
# New workflow - validate before update
def apply_seo_title(state, page_id, title, actor, config):
    # Validate first
    result = validate_seo_title(title, config=config)
    
    # Reject invalid titles
    if result["status"] == "invalid":
        raise ValidationError(f"Invalid title: {result['reason']}")
    
    # Proceed with update only if valid
    return set_page_metadata(state, page_id, title=title,
                           description=None, keywords=None, actor=actor)
```

## Testing Strategy

### Property-Based Testing

The validation function is ideal for property-based testing due to its pure functional nature. Property tests will verify universal behaviors across many generated inputs.

**Test Configuration:**
- Minimum 100 iterations per property test
- Random string generation for titles
- Random length values for max_length parameter
- Edge case coverage through generators (None, empty, boundary values)

### Unit Testing

Unit tests will cover:
- Specific examples demonstrating correct behavior
- Configuration integration (reading from Config object)
- Default value fallback behavior
- Function independence (callable without other services)

### Integration Testing

Integration tests will verify:
- Validation integration into SEO service workflows
- Proper error handling when validation fails
- Metadata updates only occur after validation passes

## Performance Considerations

**Time Complexity:**
- Empty check: O(1)
- Length check: O(1) (Python's len() is O(1) for strings)
- Overall: O(1)

**Space Complexity:**
- O(1) additional space (only creates small result dictionary)

**Scalability:**
- No database or network calls
- No state modification
- Can handle any practical title length
- Safe to call frequently (no rate limiting needed)

## Security Considerations

1. **No injection vulnerabilities**: Function only performs length checks, no parsing or evaluation
2. **No state modification**: Pure function cannot corrupt data
3. **Input sanitization**: Caller's responsibility (this function only validates length)
4. **Configuration access**: Safe read-only access to config (no writes)

## Migration and Rollout

### Phase 1: Add Validation Function
- Implement `validate_seo_title` in seo.py
- Add unit and property tests
- No changes to existing workflows

### Phase 2: Integrate into SEO Service
- Update any SEO title update functions to call validation first
- Add integration tests
- Monitor for validation rejections

### Phase 3: Monitoring
- Track validation failure rates
- Monitor "empty_title" vs "too_long" reasons
- Adjust max_length configuration if needed

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Valid Length Acceptance

*For any* string title with length between 1 and max_length inclusive, the validation function SHALL return status "valid"

**Validates: Requirements 1.4**

### Property 2: Excessive Length Rejection

*For any* string title with length exceeding max_length, the validation function SHALL return status "invalid"

**Validates: Requirements 1.5**

### Property 3: Result Type Invariant

*For any* input (title and max_length), the validation function SHALL return a dictionary

**Validates: Requirements 2.1**

### Property 4: Status Field Invariant

*For any* input (title and max_length), the validation result SHALL contain a "status" field with value either "valid" or "invalid"

**Validates: Requirements 2.2**

### Property 5: Invalid Result Contains Reason

*For any* invalid input (None, empty, or too long title), the validation result SHALL contain a "reason" field

**Validates: Requirements 2.3**

### Property 6: Empty Title Rejection

*For any* title that is None or empty string, the validation function SHALL return status "invalid" with reason "empty_title"

**Validates: Requirements 1.2, 1.3, 2.4, 2.5**

### Property 7: Too-Long Result Structure

*For any* title with length exceeding max_length, the validation result SHALL contain reason "too_long", a "length" field with the actual title length, and a "max_length" field with the configured maximum

**Validates: Requirements 2.6, 2.7, 2.8**

### Property 8: Valid Result Contains Length

*For any* valid title (length between 1 and max_length), the validation result SHALL contain a "length" field with the title length

**Validates: Requirements 2.9**

### Property 9: Validation Purity

*For any* input and state object, calling the validation function SHALL not modify the state object (validation has no side effects)

**Validates: Requirements 5.1**

## Future Enhancements

Potential extensions to consider:

1. **Whitespace Handling**: Add option to trim titles before validation
2. **Character Validation**: Validate allowed characters (e.g., no special characters)
3. **Pattern Matching**: Support regex-based validation rules
4. **Localization**: Different max_length for different locales
5. **Warning Thresholds**: Soft warnings at 80% of max_length
6. **Batch Validation**: Validate multiple titles in one call
7. **Async Validation**: Support for async validation rules (e.g., uniqueness checks)

## References

- Requirements Document: `/Users/petru-liviubouruc/Documents/PhD/Keysight/TestingTheAgents/trace-eval/.kiro/specs/seo-title-validation/requirements.md`
- Existing SEO Service: `traceeval/sut/services/seo.py`
- Configuration Service: `traceeval/sut/harness/config.py`
- Repository Service: `traceeval/sut/services/repository.py`
