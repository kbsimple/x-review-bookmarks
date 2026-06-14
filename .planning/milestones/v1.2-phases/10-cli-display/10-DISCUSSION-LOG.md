# Phase 10: CLI Display - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-06
**Phase:** 10-cli-display
**Areas discussed:** Quote tweet layout, Retweet display, Unavailable handling, Media URLs

---

## Quote Tweet Layout

| Option | Description | Selected |
|--------|-------------|----------|
| Nested Panels | Outer Panel for commentary, inner Panel for quoted content with dim border | ✓ |
| Flat layout | Single Panel with quoted content prefixed by "Quoting:" label | |
| Tree component | Rich Tree with parent/child nodes for quote structure | |

**User's choice:** Claude recommendation — Nested Panels match web nested card pattern, Rich supports natively
**Notes:** Visual hierarchy: user's quote commentary prominent, quoted content subdued

---

## Retweet Display

| Option | Description | Selected |
|--------|-------------|----------|
| Repost header + content | "[dim]Reposted from @author[/dim]" line above Panel with original content | ✓ |
| Integrated header | Retweet info inside Panel title with icon | |
| Minimal indicator | Small "♺" icon prefix, rest same as original | |

**User's choice:** Claude recommendation — Clear attribution, consistent with existing display_post() Panel style
**Notes:** Reposter info shown as "[dim]Reposted by @retweeter[/dim]" for full context

---

## Unavailable Handling

| Option | Description | Selected |
|--------|-------------|----------|
| Red-bordered placeholder | Panel with red border, "Original post unavailable" message | ✓ |
| Yellow warning style | Panel with yellow border for warning | |
| Skip silently | Don't show anything for unavailable posts | |
| Text-only message | Plain text line without Panel styling | |

**User's choice:** Claude recommendation — Red border provides visual distinction, graceful degradation
**Notes:** Show "@username" in dim if author known from reference ID

---

## Media URLs

| Option | Description | Selected |
|--------|-------------|----------|
| Numbered list with links | Indented list: "[dim]  [1] https://...[/dim]" | ✓ |
| Single line comma-separated | All URLs on one line for compactness | |
| No display | Skip media URLs in CLI (users can view in web) | |

**User's choice:** Claude recommendation — Numbered list is readable, allows user to open links
**Notes:** Prefix with 🔗 emoji for visual identification

---

## Claude's Discretion

Areas where Claude has flexibility:
- Exact Rich component styling (border colors, indentation width)
- Animation/timing for panel transitions (if any)
- Truncation length for long quoted content
- Whether to show full author display_name or just username