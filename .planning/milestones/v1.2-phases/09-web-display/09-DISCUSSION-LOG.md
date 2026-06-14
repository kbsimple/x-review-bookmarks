# Phase 9: Web Display - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-05
**Phase:** 09-web-display
**Areas discussed:** Quote tweet layout, Retweet display, Unavailable handling, Media rendering

---

## Quote Tweet Layout

| Option | Description | Selected |
|--------|-------------|----------|
| Nested card | User's quote commentary in outer card, original post in nested card with darker background and left border accent. Clear visual hierarchy. | ✓ |
| Side-by-side | User's commentary on left, original post on right in a bordered box. Better for wide screens, harder on mobile. | |
| Stacked without border | User's commentary with 'Quoting @user:' label, then original post below (no nested border). Simpler but less separation. | |

**User's choice:** Nested card
**Notes:** Clear visual hierarchy separating user's commentary from quoted content.

---

## Nested Card Styling

| Option | Description | Selected |
|--------|-------------|----------|
| Subtle gray | Gray-50 background (#F9FAFB) with gray-200 border. Subtle, matches existing card shadows. Low visual weight. | ✓ |
| Blue-tinted | Blue-50 background with blue-200 border. Highlights that it's quoted content. More visual weight. | |
| Bordered white | White background with gray-300 dashed border. Visually distinct as 'different content'. Clear separation. | |

**User's choice:** Subtle gray
**Notes:** Matches existing browse.html card styling patterns.

---

## Quote Attribution

| Option | Description | Selected |
|--------|-------------|----------|
| Label above nested card | Gray 'Quoting @username' label above the nested card. Clear but not prominent. | ✓ |
| Full attribution in nested card | Original author's avatar and name inside the nested card header. Full attribution like a regular post. | |
| Icon + label combo | Icon (quote symbol) + 'Quoting @username' text. More visual, takes more space. | |

**User's choice:** Label above nested card
**Notes:** Signals relationship without competing with original author display.

---

## Retweet Attribution

| Option | Description | Selected |
|--------|-------------|----------|
| Header with reposted label | Header line: 'Reposted from @original_author' in gray text, then the original content below. Minimal, clear. | ✓ |
| Dual avatars | Retweeter's avatar small next to original author's larger avatar. Visual but complex. | |
| Retweeter prominent | Retweet icon + retweeter username at top, original author prominent below. Emphasizes who retweeted. | |

**User's choice:** Header with reposted label
**Notes:** Minimal visual complexity with clear attribution.

---

## Retweeter Visibility

| Option | Description | Selected |
|--------|-------------|----------|
| Show retweeter above | Show retweeter avatar and username in a smaller line above the header: 'Reposted by @retweeter'. Full context. | ✓ |
| Hide retweeter info | Only show original author. Simpler but loses who retweeted it. Matches X's behavior. | |
| Show retweeter below card | Show 'Reposted by @retweeter' in a subtle line below the card. Less prominent but still visible. | |

**User's choice:** Show retweeter above
**Notes:** Full context for why this post appeared in bookmarks.

---

## Unavailable Post Placeholder

| Option | Description | Selected |
|--------|-------------|----------|
| Simple placeholder card | Gray card with 'Original post unavailable' text + generic post icon. Minimal, clear. Works well in nested layout. | ✓ |
| Placeholder with X link | Placeholder card + 'View on X' link if the user wants to check. Adds context for available author info. | |
| Placeholder with explanation | Placeholder + 'This post was deleted or the author's account is protected' explanation. More informative but takes space. | |

**User's choice:** Simple placeholder card
**Notes:** Graceful degradation without breaking the feed.

---

## Author Info for Unavailable

| Option | Description | Selected |
|--------|-------------|----------|
| Show author if known | If we know the original author (from reference ID), show '@username' in gray. Adds context for partial info. | ✓ |
| Hide author info | Just 'Original post unavailable'. No author info. Simpler, but less context. | |

**User's choice:** Show author if known
**Notes:** Partial information is better than none.

---

## Image Grid Layout

| Option | Description | Selected |
|--------|-------------|----------|
| Adaptive grid (1, 2, 3+) | Grid scales with image count: 1 image = full-width, 2 images = side-by-side, 3+ = grid. Adapts to content. | ✓ |
| 2x2 grid for 4+ images | Up to 4 images in a 2x2 grid (like X). Uses existing grid pattern from browse.html. Good for multiple images. | |
| Horizontal scroll | Horizontal scroll for multiple images. Simple, works on mobile. No grid complexity. | |

**User's choice:** Adaptive grid
**Notes:** Matches regular post card behavior, familiar to users.

---

## Image Lightbox

| Option | Description | Selected |
|--------|-------------|----------|
| Click to expand | Full-size image overlay with close button. Matches regular post card behavior. Familiar pattern. | ✓ |
| No expansion needed | Images display inline, no expansion. Simpler, but harder to see details. | |

**User's choice:** Click to expand
**Notes:** Consistent pattern, allows viewing full image.

---

## Video Handling

| Option | Description | Selected |
|--------|-------------|----------|
| Thumbnail + link to X | Show video thumbnail (if available from X API) with play icon overlay, click opens X in new tab. | ✓ |
| Text link only | Display video URLs as clickable text links. Simple, but no visual preview. | |
| Thumbnail only, no link | Show thumbnail + play icon. No click-to-play in v1.2. Defer to future milestone if needed. | |

**User's choice:** Thumbnail + link to X
**Notes:** Visual preview without complex video player implementation.

---

## Video Thumbnail Fallback

| Option | Description | Selected |
|--------|-------------|----------|
| Show preview if available | If X API returns preview_image_url, show it. If not, show a generic video icon. Simple fallback. | ✓ |
| Always use video icon | Always use video icon. No dependency on preview_image_url being available. | |

**User's choice:** Show preview if available
**Notes:** Visual preview when available, graceful fallback otherwise.

---

## Claude's Discretion

Areas where user deferred to Claude:
- Exact Tailwind CSS class names for nested cards
- Animation timing for hover effects
- Responsive breakpoints for mobile vs desktop
- Loading states while fetching embedded posts
- Error handling for failed embedded post fetches

## Deferred Ideas

None — discussion stayed within phase scope.