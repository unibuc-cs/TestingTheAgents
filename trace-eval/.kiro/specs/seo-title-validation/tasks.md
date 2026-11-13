# Implementation Plan: SEO Title Validation

## Overview

This implementation plan creates a standalone SEO title validation function that validates titles against length constraints and rejects empty titles. The validation function is a pure function that returns rich result dictionaries, making it easy to test and integrate into SEO workflows. The implementation focuses on adding the validation function to the existing SEO service module without modifying other components.

## Tasks

- [ ] 1. Implement the validate_seo_title function in traceeval/sut/services/seo.py
  - Add the `validate_seo_title(title, max_length, config)` function
  - Implement empty/None title detection returning `{"status": "invalid", "reason": "empty_title"}`
  - Implement max_length resolution from parameter, config, or default (60)
  - Implement length validation returning appropriate result dictionaries
  - Include comprehensive docstring with parameter descriptions and examples
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 3.1, 3.2, 3.3, 4.1, 4.2, 4.3, 4.4_

- [ ]* 2. Write property tests for validate_seo_title
  - [ ]* 2.1 Write property test for valid length acceptance
    - **Property 1: Valid Length Acceptance**
    - **Validates: Requirements 1.4**
    - Generate random strings with length between 1 and max_length
    - Assert that validation returns `{"status": "valid", "length": len(title)}`
  
  - [ ]* 2.2 Write property test for excessive length rejection
    - **Property 2: Excessive Length Rejection**
    - **Validates: Requirements 1.5**
    - Generate random strings with length > max_length
    - Assert that validation returns status "invalid" with reason "too_long"
  
  - [ ]* 2.3 Write property test for result type invariant
    - **Property 3: Result Type Invariant**
    - **Validates: Requirements 2.1**
    - Generate random titles (including None, empty, valid, and invalid)
    - Assert that validation always returns a dictionary
  
  - [ ]* 2.4 Write property test for status field invariant
    - **Property 4: Status Field Invariant**
    - **Validates: Requirements 2.2**
    - Generate random titles and max_length values
    - Assert that result contains "status" field with value "valid" or "invalid"
  
  - [ ]* 2.5 Write property test for invalid result contains reason
    - **Property 5: Invalid Result Contains Reason**
    - **Validates: Requirements 2.3**
    - Generate invalid inputs (None, empty, or too long titles)
    - Assert that result contains "reason" field
  
  - [ ]* 2.6 Write property test for empty title rejection
    - **Property 6: Empty Title Rejection**
    - **Validates: Requirements 1.2, 1.3, 2.4, 2.5**
    - Test with None and empty string inputs
    - Assert that validation returns status "invalid" with reason "empty_title"
  
  - [ ]* 2.7 Write property test for too-long result structure
    - **Property 7: Too-Long Result Structure**
    - **Validates: Requirements 2.6, 2.7, 2.8**
    - Generate titles longer than max_length
    - Assert result contains reason "too_long", "length", and "max_length" fields
  
  - [ ]* 2.8 Write property test for valid result contains length
    - **Property 8: Valid Result Contains Length**
    - **Validates: Requirements 2.9**
    - Generate valid titles (length 1 to max_length)
    - Assert that result contains "length" field with correct value
  
  - [ ]* 2.9 Write property test for validation purity
    - **Property 9: Validation Purity**
    - **Validates: Requirements 5.1**
    - Create a state object and call validation function
    - Assert that state object is not modified after validation

- [ ]* 3. Write unit tests for validate_seo_title
  - [ ]* 3.1 Write unit tests for specific examples
    - Test None title rejection
    - Test empty string rejection
    - Test valid title within length limit
    - Test title exactly at max_length boundary
    - Test title exceeding max_length
    - Test whitespace-only titles
  
  - [ ]* 3.2 Write unit tests for configuration integration
    - Test explicit max_length parameter
    - Test reading max_length from Config object
    - Test default fallback when both max_length and config are None
    - Test Config.get with `seo.max_title_length` key

- [ ] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 5. Add integration example for SEO service workflows
  - [ ] 5.1 Document validation integration pattern in seo.py
    - Add code comments showing how to call `validate_seo_title` before metadata updates
    - Include example of checking validation status and handling invalid results
    - _Requirements: 5.1, 5.2, 5.3_

- [ ] 6. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- The core implementation (task 1) is self-contained and adds only one function to the existing SEO service
- Property tests validate universal correctness properties across many generated inputs (minimum 100 iterations per property)
- Unit tests verify specific examples and configuration integration behavior
- The validation function is pure (no side effects) making it ideal for property-based testing
- Configuration integration allows three usage patterns: explicit max_length, config-based, or default fallback
- Integration example shows how to use validation in SEO workflows without modifying existing functions

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["2.1", "2.2", "2.3", "2.4", "2.5", "2.6", "2.7", "2.8", "2.9", "3.1", "3.2"] },
    { "id": 2, "tasks": ["5.1"] }
  ]
}
```
