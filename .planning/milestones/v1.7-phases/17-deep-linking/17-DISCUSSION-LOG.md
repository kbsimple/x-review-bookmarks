# Phase 17: Deep Linking — Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-14
**Phase:** 17-deep-linking
**Areas discussed:** What gets linked, Link generation UX, URL scheme, Filter interaction on arrival / Back link, Home button placement

---

## What Gets Linked

| Option | Description | Selected |
|--------|-------------|----------|
| Carousel, one post only | Viewer opens in carousel mode, filters cleared, exactly that post | ✓ |
| Full viewer, scrolled to post | Stream mode, all posts, scrolled/highlighted to linked one | |
| Carousel, within current filter context | Post at carousel position within active filters | |

**User's choice:** Carousel, one post only (option 1)
**Notes:** User added: "there must be a link to the home screen so the user can achieve the full app experience."

---

## Link Generation UX

| Option | Description | Selected |
|--------|-------------|----------|
| Copy button on each card | Explicit copy icon on every post card | ✓ |
| URL bar auto-updates | `history.replaceState` on every carousel nav | |
| Both | Copy button + auto-updating URL bar | |

**User's choice:** Copy button only
**Notes:** User specified: use a standard "share" icon (📤), not a text label.

---

## URL Scheme

| Option | Description | Selected |
|--------|-------------|----------|
| `#post-{id}` hash | e.g. `#post-1784230491` | ✓ |
| `?post={id}` query param | e.g. `?post=1784230491` | |
| Just the ID in hash | e.g. `#1784230491` | |

**User's choice:** `#post-{id}` hash (recommended default)

---

## Back Link / "XBM Home"

| Option | Description | Selected |
|--------|-------------|----------|
| Return to full viewer, filters cleared | Root URL, clean reset | ✓ (implied) |
| Return to full viewer, post in context | Carousel at post's position in full list | |
| Restore previous filters | Encodes filter state in URL | |

**User's choice:** Filters cleared
**Notes:** User was specific: the button label is **"XBM Home"** — not "Back to all posts". The user's framing: "the user did not come from all posts."

---

## Home Button Placement

| Option | Description | Selected |
|--------|-------------|----------|
| In the header, replacing mode switcher | Header shows XBM Home instead of Carousel/Stream | ✓ |
| Below the post card | Link row after card content | |
| Both header and below card | Redundant but always visible | |

**User's choice:** Header, replacing mode switcher (recommended default)

---

## Claude's Discretion

- Share icon visual style (exact icon, sizing, muted vs accent color)
- Copy confirmation feedback (toast, icon change, duration)
- Whether deep-link mode adds a "Linked post" label to the card

## Deferred Ideas

None.
