# Handle Stop Details in Fable 5 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Modify `claude_fable5.py` to read and handle `stop_details` (category and explanation) when a Fable 5 call is refused.

**Architecture:** Update `claude_fable5.py` to correctly extract `stop_details` from the response JSON when `stop_reason` is "refusal". Pass this information through to the `RefusalError` exception for better context.

**Tech Stack:** Python, Anthropic Messages API

## Global Constraints

- Talk Thai, coding in English.
- Follow existing patterns in `claude_fable5.py`.

---

### Task 1: Update RefusalError and logic in claude_fable5.py

**Files:**
- Modify: `claude_fable5.py`
- Test: Create a temporary test script or use an existing test if available.

**Interfaces:**
- `RefusalError`: Now accepts `category` and `explanation` instead of just `classifier`.

- [ ] **Step 1: Modify RefusalError class**

```python
class RefusalError(Exception):
    """Raised when a Fable 5 call is refused and fallback is disabled/exhausted."""
    def __init__(self, message: str, category: Optional[str] = None, explanation: Optional[str] = None):
        super().__init__(message)
        self.category = category
        self.explanation = explanation
```

- [ ] **Step 2: Update call_with_fallback to extract stop_details**

```python
    def call_with_fallback(self, prompt: str, system: Optional[str] = None,
                           allow_fallback: bool = True) -> dict:
        # ... (keep existing code for calling)
        data = self.call(prompt, system=system)
        # ... (handle errors)

        stop_reason = data.get("stop_reason")
        refused = stop_reason == "refusal"
        
        # New logic to extract stop_details
        stop_details = data.get("stop_details", {})
        category = stop_details.get("category")
        explanation = stop_details.get("explanation")
        classifier = category # Keep for backward compatibility

        if refused and allow_fallback:
            # ... (keep existing fallback logic)
            # Update RefusalError construction if needed here (but this is inside if refused...)
            # Actually, if allow_fallback is True, we don't raise RefusalError here.
            
            # ...

        if refused:
            # Update raising RefusalError with new arguments
            raise RefusalError(
                f"Claude Fable 5 declined this request (category: {category or 'unspecified'}, explanation: {explanation or 'none'}). "
                "Re-run with fallback enabled, or use claude-opus-4-8 directly.",
                category=category,
                explanation=explanation
            )
        
        # ... (return result)
```

- [ ] **Step 3: Update return dict for non-refusal or fallback-handled cases**

Ensure the return dictionary in `call_with_fallback` includes `category` and `explanation` to be consistent.

- [ ] **Step 4: Commit**

```bash
git add claude_fable5.py
git commit -m "feat: handle stop_details in Fable 5 refusal responses"
```
