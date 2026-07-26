# GH-015 Plan: Polish The Music Channel

# What

- Give the existing Music channel one focused visual polish pass.
- Improve at-a-distance hierarchy, album-art treatment, playback status,
  metadata legibility, progress, and narrow-screen behavior.
- Preserve every accepted loaded, playing, paused, stopped, unavailable,
  connecting, initial-loading, and artwork-fallback state.
- Keep the current Spotify receiver, playback payload, projection behavior,
  action feedback, and explicit channel shell unchanged.

## Out Of Scope

- Today redesign or weather changes.
- Spotify authentication, Web API use, playback transport controls, queue,
  browsing, lyrics, recommendations, or receiver changes.
- New payload fields, coordinator behavior, endpoint provisioning, shortcuts,
  channel IDs, camera behavior, or agent interaction.
- A component library, animation library, router, registry, theme system, or new
  frontend dependency.
- Replacing the accepted warm room palette across the complete application.

## Deferred

- GH-017 adds Camera after the explicit shell and Music polish exist.
- Any shared design tokens or reusable channel layout wait until another real
  channel repeats the same choice.
- Spotify transport control remains deferred because the iPhone app is the
  accepted controller.

## Acceptance Criteria

- [ ] Loaded Music has a clear first glance at artwork, title, creator, playback
  state, and progress from the iMac's normal room distance.
- [ ] Playing and paused remain visually distinct without relying only on color.
- [ ] Track and episode labels, collection, elapsed time, duration, and
  accessible progress labeling remain present and accurate.
- [ ] Very long title, creator, and collection values remain readable or
  intentionally bounded without overlapping artwork, progress, or room
  feedback.
- [ ] Missing, rejected, or failed remote artwork retains an intentional,
  accessible local fallback.
- [ ] Stopped, unavailable, connecting, and first-observation states receive the
  same visual quality as loaded playback and retain clear recovery guidance.
- [ ] The deployed 1920×1200 view and representative narrow and wide browser
  sizes have no clipping, accidental scrolling, unreadable scale, or overlay
  collision.
- [ ] Channel, connection, identify, scene, and future voice feedback remain
  shell-owned and visible above Music.
- [ ] Reduced-motion behavior remains respected and decorative media remains
  hidden from assistive technology.
- [ ] No playback schema, Spotify integration, action, shortcut, dependency,
  coordinator, endpoint, or service change is introduced.
- [ ] Focused render tests cover every Music state and meaningful long-content
  boundary.
- [ ] Biome, frontend tests, production build, production audit, Python suites,
  and whitespace checks pass.

# Tasks

## 1. Polish Loaded Playback

- Refine `MusicChannel.jsx` and Music-specific styles around the accepted
  content hierarchy.
- Keep artwork URL validation, projection timing, accessible labels, and
  playback semantics unchanged.
- Cover long track, creator, and collection content explicitly.

## 2. Polish Empty And Failure States

- Bring stopped, unavailable, connecting, initial-loading, and artwork-fallback
  presentation to the same level as loaded playback.
- Preserve exact recovery meaning and state selection.

## 3. Qualify Responsive And Shared Feedback Behavior

- Add focused server-rendered assertions for all states and content bounds.
- Review 1920×1200 plus narrow and wide viewports with shared feedback overlays.
- Create `docs/wip/GH-015.md` with the visual walkthrough, before/after
  description, automated checks, and exact reviewer actions.

# Heatmap

Reference: `../project/HEATMAP.md`.

## Hot

### H1 - Improve Music Without Changing Its Contract

- Decision: Treat this as a presentation-only issue.
- Proposed approach: Limit product changes to the Music component,
  Music-specific CSS, and focused tests while consuming the existing playback
  projection unchanged.
- Why: The accepted receiver and normalized playback path already work, and a
  visual pass should remain independently reviewable.
- Alternatives: Add Spotify Web API fields; add controls; redesign the shell;
  combine Camera work.
- Review focus: No hidden payload, action, endpoint, or integration changes.

## Stylistic

### S1 - Preserve The Warm Retro-Futuristic Room Character

- Choice: Evolve the existing warm dark palette, oversized typography, tactile
  artwork, and restrained glow rather than imitate Spotify's application UI.
- Alternative: Spotify-green branding; a generic dashboard card; a completely
  new site-wide theme.
- When to apply: Loaded Music, every empty/failure state, and artwork fallback.
