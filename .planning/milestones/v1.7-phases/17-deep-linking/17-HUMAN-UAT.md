---
status: partial
phase: 17-deep-linking
source: [17-VERIFICATION.md]
started: 2026-06-14T22:45:00Z
updated: 2026-06-14T22:45:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Share icon clipboard copy
expected: Click 📤 on a post card at the Netlify deploy; URL of form `#post-{id}` is copied to clipboard and brief "Copied!" visual confirmation appears on the icon
result: [pending]

### 2. Deep link hash navigation
expected: Open `https://xbm-viewer-export.netlify.app/#post-{valid_id}`; viewer opens in carousel mode with filters cleared, linked post shown, "XBM Home" button in header (mode switcher hidden)
result: [pending]

### 3. XBM Home navigation
expected: From a deep link URL, click "XBM Home"; navigates cleanly to root URL with no `#` fragment; mode switcher returns to header
result: [pending]

### 4. Post not found error
expected: Open `#post-fake999`; "Post not found" message appears with XBM Home link; no crash or blank screen
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps
