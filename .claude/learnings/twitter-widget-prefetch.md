# Learnings: Twitter Widget Prefetch System

Debugging session that fixed blocking navigation latency in the static viewer's
carousel mode. Three stacked bugs, all discovered via Playwright telemetry.

---

## Bug 1 — `twttr.events.bind('rendered')` passes an event object, not the element

### Symptom
`widget-ready` was never set on any `.oembed-container`. Every carousel navigation
fell through to a foreground `loadTwitterWidget()` call regardless of whether the
post was pre-warmed in the prefetch pool. Telemetry showed:

```
[WIDGET] rendered no-container el=undefined
```

### Root cause
`twttr.events.bind('rendered', handler)` fires with a Twitter **event object**
`{ target: iframe, type: 'rendered', ... }` as the argument — NOT the iframe
element directly. Our handler assumed it received the element:

```javascript
// BROKEN — el is the event object, not the iframe
function _onWidgetRendered(el) {
  el.closest('.oembed-container'); // undefined — event objects have no .closest
}
```

### Fix
Extract `.target` from the event object before walking the DOM:

```javascript
function _onWidgetRendered(event) {
  var el = (event && event.target) ? event.target : event; // guard for API changes
  var container = el && el.closest ? el.closest('.oembed-container') : null;
  ...
}
```

### Rule
Any time `twttr.events.bind('rendered', fn)` is used, the handler parameter is
an event object. Always read `.target` from it.

---

## Bug 2 — `visibility:hidden` on a parent cascades to blockquotes, breaking widget processing

### Symptom
Prefetch pool was populated and `twttr.widgets.load(prefetchContainer)` was being
called, but `widget-ready` was never set on pool nodes. Pool hits on navigation
always showed `widget_ready=false`.

### Root cause
`visibility:hidden` is an **inherited** CSS property. The off-screen prefetch
container was styled with it:

```javascript
_prefetchContainer.style.cssText =
  'position:absolute;left:-9999px;top:-9999px;width:500px;visibility:hidden;pointer-events:none;';
```

Every `blockquote.twitter-tweet` inside the container inherited `visibility:hidden`.
`twttr.widgets.load()` silently skips elements with this style — no iframe is created,
no `rendered` event fires, `widget-ready` is never set.

This same class of bug appeared twice in this project:
- First occurrence: CSS rule `.oembed-container:not(.widget-ready) blockquote { visibility: hidden }` added as a "hide raw blockquote while loading" measure — caused 15–30s stalls.
- Second occurrence: `visibility:hidden` on the prefetch container itself.

### Fix
Replace `visibility:hidden` with `opacity:0`. The container is already off-screen
at `left:-9999px`; `opacity` does not cascade to children, so Twitter processes
the blockquotes normally:

```javascript
_prefetchContainer.style.cssText =
  'position:absolute;left:-9999px;top:-9999px;width:500px;opacity:0;pointer-events:none;';
```

### Rule
Any container passed to `twttr.widgets.load()`, or any ancestor of a
`.twitter-tweet` blockquote, must **never** use `visibility:hidden`. Use
`opacity:0` + off-screen positioning instead.

---

## Bug 3 — Prefetch runs before widgets.js loads; pool nodes never background-processed

### Symptom
On the first post, `_runPrefetch` fires during idle time and warms posts 1 and 2
in the prefetch container. But `twttr_ready=false` at that moment, so
`twttr.widgets.load(prefetchContainer)` is not called. The backfill never happens,
so posts 1 and 2 arrive in the pool without `widget-ready` even after Bug 2 was fixed.

### Fix
In the `widgets.js` `onload` handler, after processing `post-list`, also process
any already-warmed pool nodes:

```javascript
s.onload = function() {
  twttr.widgets.load(document.getElementById('post-list'));
  // Backfill pool nodes warmed before twttr was ready
  if (prefetchPool.size > 0 && _prefetchContainer) {
    twttr.widgets.load(_prefetchContainer);
  }
};
```

### Rule
After injecting `widgets.js`, always check whether the prefetch pool was populated
before the script loaded and process it in the `onload` callback.

---

## Debugging Methodology

### Instrument first, guess never

Add a `_log(category, message)` function that writes timestamped entries to
`console.log` and an internal buffer. Log at every async lifecycle point:

| Point | What to log |
|-------|-------------|
| `renderCarousel` | `idx`, `pool_hit`, `widget_ready` |
| `loadTwitterWidget` | `twttr_ready`, `script_loaded` |
| `_onWidgetRendered` | `container.id`, `in_prefetch` |
| `_runPrefetch` | window range, `already_pooled`, `widget_ready`, `twttr_ready` |
| `_setupSkeletonFallback` | `iframe` present, `already_ready` |

### Use Playwright to navigate headlessly

Don't manually test widget bugs in a browser. Use `scripts/e2e_debug_check.js`:

```javascript
const { chromium } = require('playwright');
page.on('console', msg => { if (msg.text().includes('[XBM:')) logs.push(msg.text()); });
await page.goto('https://xbm-viewer-export.netlify.app/', { waitUntil: 'networkidle' });
await page.waitForSelector('#carousel-next');
// navigate + collect logs per post
```

### What good output looks like

```
[RENDER] idx=1 id=XXX pool_hit=true widget_ready=true   ← pool hit, skip loadTwitterWidget
[RENDER] idx=2 id=YYY pool_hit=true widget_ready=true
[PREFETCH] already_pooled id=ZZZ widget_ready=true       ��� downstream posts pre-warmed
```

Pool hits from post 1 onward should have `widget_ready=true`. If they show
`widget_ready=false`, check for the three bugs above.

### Don't call a fix done without reading the telemetry

Running the Playwright script takes ~30 seconds and shows definitively whether
pre-warming is working. "It seems faster" is not a valid confirmation.

---

## Gotchas

- **`const` is not on `window`** — top-level `const`/`let` in a `<script>` tag are
  NOT properties of `window`. Use `var` for anything you want to inspect via
  `page.evaluate(() => window.X)`.
- **`#debug` hash sets `deepLinkMode=true`** — the debug overlay calls
  `deepLinkMode = true`, which causes `renderView()` to return early, so the
  carousel never renders. Navigate the normal URL and read `console.log` output
  instead of relying on the overlay.
- **Deploy races** — `xbm export-static` is slow. If the export is run as a
  background task and the deploy runs immediately, the stale `data/static-export/`
  is deployed. Always chain them: `venv/bin/xbm export-static --rich-embeds && netlify deploy ...`.
