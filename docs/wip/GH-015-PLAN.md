# GH-015 Plan: Polish The Music Channel

# What

- Keep the accepted Music player layout while replacing its Cortex Home,
  playback-state, and item-type strip with one Spotify icon and `Spotify`
  source label.
- Show the persistent Hue scene badge only on the Home view, which is the
  existing Today channel.
- Add an application-owned secondary Music view that toggles with `Ctrl`+`M`
  only while Music is active.
- Turn that secondary view into an artwork-led fullscreen composition with
  adaptive side color and progress-filled rotated typography.
- Repair the coordinator deployment manifest so the existing room-context
  module reaches the server and deployment verifies runtime imports before
  restarting the service.
- Preserve the current Spotify receiver, playback payload, projection behavior,
  action feedback, channel selection, and kiosk deployment.

## Out Of Scope

- Bluetooth, general system audio, additional playback sources, source
  selection, or source detection.
- Spotify authentication, Web API use, playback transport controls, queue,
  browsing, lyrics, recommendations, or receiver changes.
- Browser Fullscreen API integration, function-key remapping, or changes to the
  Chromium kiosk.
- New payload fields, coordinator behavior, endpoint provisioning, channel IDs,
  camera behavior, or agent interaction.
- A component library, icon dependency, router, registry, theme system, or new
  frontend dependency.

## Deferred

- A live upcoming-item metadata source remains deferred because the current
  librespot event contract exposes only the upcoming Spotify identifier, not
  the complete title, artist, and artwork needed by the accepted design.
- Additional source labels wait until another playback source actually exists.
- GH-017 adds Camera independently after the explicit channel shell exists.
- Spotify transport control remains deferred because the iPhone app is the
  accepted controller.

## Acceptance Criteria

- [ ] Loaded Music shows only a Spotify icon and `Spotify` for source identity;
  it no longer shows `Cortex Home`, `Now playing`, `Paused`, `/ Music`, or
  `/ Episode` in the former heading strip.
- [ ] Artwork, title, creator, collection, elapsed time, duration, accessible
  progress labeling, and playback projection remain present and accurate.
- [ ] Track and episode payloads, long metadata, missing artwork, stopped,
  unavailable, connecting, and first-observation states retain their current
  behavior and recovery meaning.
- [ ] Empty and failure Music states use the same Spotify source identity
  instead of `Cortex Home / Music`.
- [ ] Stopped Music shows only the Spotify mark/name above `Choose
  "Högtalaren" as speaker in Spotify to connect`; it has no separate stopped
  heading, explanation, or status label.
- [ ] The persistent active Hue scene badge is visible on Home/Today and absent
  from both normal and secondary Music views.
- [ ] Normal Music retains connection, channel, identify, and transient scene
  action feedback; the secondary view renders no normal player or shared
  feedback.
- [ ] Pressing non-repeating `Ctrl`+`M` without other modifiers while Music is
  active toggles between normal Music and the fullscreen view without a
  coordinator request.
- [ ] `Ctrl`+`M` does not toggle the secondary view while Home/Today is active,
  and leaving Music resets the secondary view so returning to Music starts in
  the normal view.
- [ ] Existing `Ctrl`+`Alt` channel and scene shortcuts retain their exact
  behavior.
- [ ] Fullscreen Music shows one centered square artwork with the surrounding
  screen filled by the artwork's most common sampled color.
- [ ] The current title and creators form an upper-left-aligned stack, with
  creators directly below the title, and are rotated `-90deg`; no source,
  album, elapsed time, duration, or additional player element appears.
- [ ] The current title fills from its cover's recurring distinctive color to
  a contrast-selected pure black or white at 60% opacity according to projected
  playback progress; creators use the same monochrome color at 40% opacity.
- [ ] If complete upcoming-item metadata is available, its smaller rotated
  title and creators appear only in the final ten seconds, fill over those ten
  seconds from the upcoming cover's distinctive color, and fall back to
  contrast-selected black or white when that color cannot be resolved.
- [ ] A transient item-less snapshot at a track boundary retains the last
  complete track for 800ms instead of flashing black.
- [ ] A confirmed track change swipes the previous artwork and metadata left
  while the new track enters from the right over a sharp 400ms ease-in-out
  animation; the surrounding majority color fades to the new color.
- [ ] The deployed 1920×1200 view and representative narrow and wide browser
  sizes have no new clipping or accidental scrolling.
- [ ] Reduced-motion behavior and decorative-media accessibility remain
  unchanged.
- [ ] No playback schema, Spotify integration, action, dependency, coordinator,
  runtime behavior, endpoint, or service contract change is introduced.
- [ ] Coordinator deployment includes every local module imported by
  `cortex_home.py` and verifies that the installed coordinator imports before
  restarting the service.
- [ ] Focused tests cover source identity, Home-only lighting status,
  fullscreen content boundaries, palette selection, final-ten-second upcoming
  presentation, and `Ctrl`+`M` classification.
- [ ] Biome, frontend tests, production build, production audit, Python suites,
  and whitespace checks pass.

# Tasks

## 1. Replace The Music Heading Strip With Source Identity

- Add one local, accessible Spotify source mark without introducing an icon
  package or remote asset.
- Use it in loaded, empty, and failure Music presentations.
- Remove playback state and item type only from the former heading strip while
  preserving the rest of the player contract.

## 2. Keep Persistent Lighting Status On Home

- Let shared feedback render the persistent Hue scene badge only when Today is
  active.
- Preserve the existing scene shortcut, scene action lifecycle, and transient
  scene feedback in normal channel views.
- Add render assertions for the visible and hidden badge states.

## 3. Add The Fullscreen Music View

- Classify non-repeating `Ctrl`+`M` without other modifiers separately from
  coordinator keyboard actions.
- Keep the toggle as local application state, allow it only for observed Music,
  and reset it when another channel becomes active.
- Center the square cover and extend its majority color into the unused screen
  area without adding more player chrome.
- Stack the title above its creators with upper-left alignment, rotate the
  typography, make the current title the playback progress indicator, and
  choose a recurring distinctive cover color for its completed portion.
- Choose pure black or white for maximum computed background contrast.
- Render the unplayed title portion at 60% opacity and creators at 40%.
- Support the final-ten-second upcoming treatment when complete metadata exists
  and use monochrome as its unresolved-palette fallback.
- Temporarily retain the previous complete track across item-less boundary
  snapshots, then animate confirmed changes with a sharp 400ms left swipe and
  background-color fade.
- Omit normal channel content, shared overlays, source, album, and time
  metadata.

## 4. Confirm The Narrow Change

- Include the existing `context.py` runtime dependency in both coordinator
  deployment stages and add an installed-import preflight.
- Add a regression check that compares local coordinator imports with both
  deployment scripts.
- Run focused state and server-rendered component assertions.
- Run the complete frontend and Python checks, production build and audit, and
  whitespace validation.
- Create `docs/wip/GH-015.md` only when the full Music issue is ready for final
  review, including the later secondary-view design.

# Heatmap

Reference: `../project/HEATMAP.md`.

## Hot

### H1 - Keep The Secondary View Local To Music Presentation

- Decision: Treat `Ctrl`+`M` as a local Music presentation toggle rather than a
  new coordinator channel, action, or browser fullscreen request.
- Proposed approach: Classify the exact key locally, render the artwork-led
  Music presentation while active, and reset it on observed channel exit.
- Why: The display already runs as a Chromium kiosk, and the requested mode
  changes only how the active Music channel is presented.
- Alternatives: Add a coordinator action; add a channel ID; call the browser
  Fullscreen API; change kiosk launch flags.
- Review focus: Exact key handling, no network request, exit behavior, and
  absence of normal overlays in the fullscreen view.

### H2 - Move Only Persistent Lighting Presentation

- Decision: Scope Home ownership to the persistent active-scene badge.
- Proposed approach: Keep shared feedback behavior intact but conditionally
  render its lighting status only for Today.
- Why: Scene activation and failure still need immediate feedback, while the
  steady-state badge is contextual information the user wants anchored to Home.
- Alternatives: Remove all scene feedback from Music; move Hue state into the
  Today payload; duplicate feedback components.
- Review focus: Home visibility, Music absence, and unchanged scene actions.

## Stylistic

### S1 - Name The Current Source Without Adding Player Chrome

- Choice: Use Spotify's circular mark and name as a restrained source label in
  the space previously occupied by the multi-part status strip.
- Alternative: Retain Cortex Home branding; retain playback state and item
  type; add a source selector.
- When to apply: Loaded, empty, and failure Music presentations only.

### S2 - Let Artwork And Typography Be The Fullscreen Interface

- Choice: Show only centered square artwork, adaptive surrounding color, and
  rotated title/creator typography whose title fill communicates progress.
- Alternative: Reuse the normal player, add controls or numeric progress, or
  retain room feedback overlays.
- When to apply: The secondary Music presentation in this issue.
