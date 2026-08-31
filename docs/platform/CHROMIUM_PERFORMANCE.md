# Chromium Performance On The iMac

## Finding

Do not add SSR, Astro, or another frontend framework to fix the channel
transition. Those choices can improve initial HTML delivery and reduce startup
JavaScript, but Cortex Home stays loaded as one kiosk document and changes
channels from live coordinator state. The lag happens during a later visual
transition inside Chromium, after any server-rendered HTML would already be
hydrated.

The selected behavior is the cheapest and most reliable option: an immediate
cut. Every observed `channel.active` snapshot dispatches directly with no
animation layer, snapshot, retained tree, timer, or transition promise.

A solid fade-through-black was also prototyped because it avoids channel
snapshots, but its first deployed sequencing path reported a completed action
while leaving Chromium on Today. The timer-based correction passed locally;
the user still chose the smaller and more reliable instant-cut boundary.

Keep the current architecture until an iMac trace shows that JavaScript, rather
than painting or compositing, is the bottleneck.

## Why The Previous View Transition Lagged

The first implementation named the channel surface and called
`document.startViewTransition` for observed Today/Music changes. Camera,
AirPlay, and Music fullscreen deliberately remain immediate privacy and native
composition cuts, which is why that animation appeared only between Today and
Music.

Chrome documents that a same-document View Transition captures the old named
elements, updates the DOM while rendering is suppressed, captures the new
state, and animates snapshot pseudo-elements in an overlay. That is convenient,
but it creates work proportional to the visual surface being captured.

The kiosk renders at 1920×1200. One uncompressed 32-bit full-screen image is
approximately 8.8 MiB:

```text
1920 × 1200 × 4 bytes = 9,216,000 bytes = 8.79 MiB
```

An old and new full-screen image therefore represent roughly 17.6 MiB of pixel
data before extra compositor buffers and browser overhead. This is an inference
from the documented snapshot model, not a measured Chromium allocation. On an
older GPU, capturing, uploading, and blending those surfaces is a more plausible
cause of the observed lag than React state dispatch or network latency.

The final production bundle is about 274 kB JavaScript / 86 kB gzip and 38 kB
CSS / 8 kB gzip. Bundle parsing affects startup; it does not repeat for every
channel change.

## Ranked Alternatives

| Rank | Approach | Runtime cost | Fit |
|---|---|---:|---|
| 1 | Immediate cut | Lowest | Selected for every channel on the current iMac. |
| 2 | Solid curtain or fade-through-black over an immediate cut | Very low | Rejected after the prototype complicated and briefly blocked the basic state update. |
| 3 | Incoming-view-only `transform`/`opacity` animation | Low to medium | No outgoing snapshot, but the new full-screen view may still need a large paint and texture upload. |
| 4 | Previous View Transition snapshots | Medium to high on this iMac | Simple and polished on capable hardware, but the observed result says its full-screen snapshot path is too expensive here. |
| 5 | Keep two live channel trees and slide them | High | Retains effects, media, and memory; conflicts with synchronous Camera cleanup and AirPlay boundaries. |
| 6 | Canvas/WebGL transition | High complexity, uncertain cost | Adds a rendering system and still moves large textures. Not justified for four views. |

The final implementation performs only the React state update already required
to display the observed channel. The rejected fade remains a viable visual
technique on different hardware, but it is not part of Cortex Home.

A directional curtain can preserve the sense of next/previous navigation
without moving any channel pixels. A fade-through-black is even simpler. Avoid
blur, `backdrop-filter`, animated shadows, masks, clip paths, layout properties,
and simultaneous full-screen opacity blends on this hardware.

## SSR, Astro, And Framework Alternatives

### Server-Side Rendering

SSR sends initial HTML before client JavaScript loads, then hydration attaches
the interactive React logic. React's documentation describes hydration as an
initial-load mechanism. It does not replace client-side state updates after the
application is interactive.

For Cortex Home, SSR would:

- improve the first visible shell only if startup is currently slow;
- add a server render/hydration boundary around browser-only camera, audio,
  keyboard, timer, and EventSource behavior;
- leave every later channel transition inside Chromium;
- leave snapshot and GPU compositing cost unchanged.

Recommendation: do not implement SSR for transition performance.

### Astro

Astro's islands model is effective when most of a page is static HTML and only
small widgets need client JavaScript. Cortex Home is the inverse: the persistent
shell, active channel, keyboard authority, voice phases, camera, AirPlay
control, playback, clock, weather, lighting, and the new metrics overlay all
depend on live client behavior.

Wrapping the current app as one hydrated React island would retain almost all
runtime work. Splitting it into many islands would add coordination boundaries
without changing the compositor cost of moving full-screen pixels.

Recommendation: do not migrate to Astro for this issue. Reconsider it only if
Cortex Home becomes mostly static multi-page content.

### Preact, Vanilla DOM, Or A Multi-Page App

- Preact or smaller client code could reduce startup parse and memory slightly,
  but would not change full-screen transition texture cost.
- Vanilla DOM code could reduce React work, but the current observed channel
  update is small. Migrate only if a Performance trace attributes missed frames
  to JavaScript or React commits.
- A multi-page application would replace the persistent live shell with
  document navigations, duplicate connection setup, and complicate Camera,
  voice, and room feedback. Cross-document View Transitions still use browser
  snapshots.

Recommendation: keep the current React/Vite single document.

## How To Measure Before Changing Architecture

Use the new `Ctrl`+`Alt`+`M` overlay to correlate lag with CPU, memory pressure,
load, and temperature. It reports real iMac data from `/proc` and Linux thermal
sysfs every two seconds only while visible. It is diagnostic context, not a
frame profiler.

If channel motion is reconsidered on different hardware:

1. Confirm hardware acceleration in `chrome://gpu`. A software compositor
   changes the diagnosis completely.
2. Record Today → Music and Music → Today in Chrome DevTools Performance.
3. Enable the Rendering panel's FPS meter and paint flashing.
4. Compare three builds: the accepted immediate cut, the previous View
   Transition, and an isolated solid-overlay fade.
5. Record dropped frames, raster/paint time, compositor activity, CPU,
   temperature, and memory at the same 1920×1200 viewport.
6. Prefer the simplest transition that remains visually acceptable on the
   physical iMac.

Do not add persistent `will-change` declarations speculatively. Extra layers
consume memory and texture bandwidth; add temporary promotion only if the trace
shows it helps.

## Sources

- [Chrome: same-document View Transitions](https://developer.chrome.com/docs/web-platform/view-transitions/same-document)
  explains the old/new snapshot model, overlay pseudo-elements, rendering
  suppression, progressive-enhancement behavior, and current layout-animation
  caveat.
- [Chrome: View Transition overview](https://developer.chrome.com/docs/web-platform/view-transitions)
  confirms that SPA and multi-page transitions use the same snapshot and CSS
  animation building blocks.
- [web.dev: high-performance CSS animations](https://web.dev/articles/animations-guide)
  recommends compositor-friendly `transform` and `opacity`, measuring with the
  FPS meter and paint flashing, and using `will-change` sparingly.
- [web.dev: why animations are slow](https://web.dev/articles/animations-overview)
  explains the style/layout/paint/composite pipeline and warns that layers use
  memory and CPU-to-GPU bandwidth.
- [React: `hydrateRoot`](https://react.dev/reference/react-dom/client/hydrateRoot)
  defines hydration as attaching React to server-generated initial HTML.
- [Astro: islands architecture](https://docs.astro.build/en/concepts/islands/)
  describes Astro's advantage when mostly static HTML surrounds small,
  independently hydrated interactive regions.
- [Astro: migrate an existing project](https://docs.astro.build/en/guides/migrate-to-astro/)
  identifies content-oriented sites as Astro's primary fit and notes that
  interactive UI still requires client scripts or framework components.
