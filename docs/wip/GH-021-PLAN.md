# GH-021 Plan: Redesign The Home Screen

# What

- Redesign the existing Today channel as Cortex Home's calm default home screen
  for room-scale reading.
- Keep the current local clock, date, Linköping weather, three-day forecast,
  attribution, and unavailable state while improving hierarchy, balance,
  spacing, and responsive behavior.
- Preserve the channel, coordinator, weather, lighting, voice, and shared
  feedback contracts.

## Out Of Scope

- New data, widgets, accounts, providers, calendar, tasks, news, location
  configuration, personalization, or user-editable layout.
- Coordinator, SSE, weather cache, keyboard, voice, Hue, RoomFeedback, Music,
  Camera, AirPlay, or channel-transition behavior.
- A component library, icon dependency, remote font, remote image, or reusable
  dashboard/grid system.
- Renaming the coordinator's `today` channel or changing its shortcut.

## Deferred

- Additional daily context waits until a concrete source and glanceable user
  flow justify a separate issue.
- Configurable layouts and reusable widgets remain deferred because one fixed
  home composition does not establish a useful extension contract.
- Shared visual-system extraction waits until the redesigned Home screen and
  existing Music, Camera, and AirPlay presentations reveal a repeated pattern.

## Acceptance Criteria

- [ ] The default screen reads unmistakably as Cortex Home at a distance, with
  time as the primary element and date, current weather, location, and forecast
  in a clear secondary hierarchy.
- [ ] The redesign uses only the existing normalized Today snapshot and local
  clock; no request, state, storage, dependency, or coordinator contract is
  added.
- [ ] Available weather shows the exact current temperature and condition plus
  all three existing forecast days with high, low, and condition values.
- [ ] Unavailable weather remains a composed, intentional home screen with
  useful time and date rather than a broken grid, blank panel, or stale-looking
  forecast.
- [ ] MET Norway attribution remains visible and legible without competing
  with glanceable content.
- [ ] Shared connection, lighting, identify, channel-action, voice, and debug
  feedback remains above the Home presentation and readable in idle, working,
  success, and failure states.
- [ ] The layout has no overlap, clipping, accidental scroll, or unreadably
  small copy at the deployed iMac viewport and representative narrow, short,
  and wide browser viewports.
- [ ] Long dates, every accepted weather condition, negative and double-digit
  temperatures, and three forecast cards retain stable hierarchy.
- [ ] The implementation remains one explicit `TodayChannel` rather than
  introducing widgets, configuration, routing, or a generic dashboard.
- [ ] Focused presentation tests cover available and unavailable weather,
  semantic forecast labeling, attribution, and stable content ownership.
- [ ] Biome, frontend tests, production build, production audit, Python suites,
  endpoint tests, shell syntax, compilation, and whitespace checks pass.
- [ ] The reviewer confirms the physical iMac result is calmer, more balanced,
  and more readable from normal room distance than the previous Home screen.

# Tasks

## 1. GH-021: Redesign The Home Screen

- Recompose `TodayChannel` into one fixed responsive home layout using the
  existing data and project stack, then update its focused available and
  unavailable presentation tests.
- This is atomic because the layout, hierarchy, and responsive treatment form
  one visual change with no behavior or contract change.

# Heatmap

Reference: `../project/HEATMAP.md`.

## Hot

### H1 - Compose One Calm Default Screen

- Decision: Replace the current stacked status layout with a more deliberate
  room-scale home composition without turning Today into a dashboard system.
- Proposed approach: Use an asymmetric two-zone layout: a dominant clock and
  date anchor paired with a compact current-weather and three-day forecast
  region, surrounded by enough negative space for shared room feedback.
- Why: The default view should be readable in a glance and feel intentional on
  the 16:10 iMac while still adapting to development and narrow viewports.
- Alternatives: Keep the current vertical stack; use equal dashboard cards;
  add a configurable widget grid; make weather the dominant element.
- Review focus: distance hierarchy, visual balance, empty space, feedback
  collisions, and whether the unavailable state still feels complete.

### H2 - Keep Presentation Local To Today

- Decision: Contain the redesign in `TodayChannel` and focused tests rather than
  changing the shell or extracting a premature shared design system.
- Proposed approach: Use Tailwind utilities and, only where necessary, a small
  Today-specific style in the existing stylesheet.
- Why: GH-020 owns channel replacement and the other channels already have
  intentionally different full-screen visual languages.
- Alternatives: Restyle the complete shell; extract generic cards and grids;
  redesign RoomFeedback in the same issue.
- Review focus: file ownership, merge independence, component naming, and no
  leaked behavior changes.

## Stylistic

### S1 - Warm Retro-Futuristic Restraint

- Choice: Keep the accepted warm dark palette and strong typography, using
  restrained borders, glow, and grid texture to add depth without making the
  screen busy.
- Alternative: Bright dashboard cards, photoreal weather art, skeuomorphic
  controls, or a new visual theme.
- When to apply: To the Home/Today presentation only; shared feedback and other
  channels retain their current styles.
