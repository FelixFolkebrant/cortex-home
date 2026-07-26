# GH-013 Plan: Separate The Channel Shell

# What

- Split the existing Today and Music views out of `App.jsx`.
- Rename the shared reducer, projection, and keyboard module so it describes
  room state instead of only Music.
- Extract shared connection, lighting, channel-toast, and room-action feedback
  from channel presentation.
- Keep one explicit Today/Music switch and preserve every current payload,
  shortcut, action, visual state, and dependency.

## Out Of Scope

- Visual redesign, copy changes, new responsive behavior, or channel polish.
- Headlines, another provider, another shortcut, or another channel ID.
- A router, registry, configuration file, plugin API, component library, or
  separate application build.
- Coordinator, endpoint, Python, deployment, CSP, or service changes.
- Agent context, model, microphone, speech, or agent feedback.

## Deferred

- GH-015 performs the visible Today and Music polish after file ownership is
  clear.
- GH-017 adds Headlines to the explicit switch after its real state and view
  exist.
- Voice feedback remains in Planpoint 4 and will integrate with the shared shell
  only after this behavior-preserving split merges.

## Acceptance Criteria

- [ ] Today presentation and its local clock live in one explicit channel
  component.
- [ ] Loaded, stopped, unavailable, progress, and artwork-fallback Music
  presentation live in one explicit channel component.
- [ ] Initial room state, reducer, playback projection, formatting helpers,
  scene cycling, and fixed keyboard classification live in an accurately named
  shared room-state module.
- [ ] Connection, lighting, channel toast, identify, and scene overlays remain
  outside channel components and render above either channel.
- [ ] `App.jsx` owns the single endpoint connection, action submission
  lifecycle, and explicit active-channel switch without a router or registry.
- [ ] Today and Music render the same accepted copy, hierarchy, classes, and
  attribution as before.
- [ ] `Ctrl`+`Alt`+`1`, `Ctrl`+`Alt`+`2`, and `Ctrl`+`Alt`+`S` retain exact
  behavior and ignored modifier/repeat rules.
- [ ] Playback, Today, lighting, channel, connection, and interaction reducer
  behavior remains independent.
- [ ] Existing frontend tests are moved or renamed without losing assertions;
  focused component boundaries are covered where extraction introduces them.
- [ ] Biome, frontend tests, production build, production audit, Python suites,
  and whitespace checks pass.
- [ ] The durable issue record names the new file ownership boundary and
  confirms that no visual or contract change was intended.

# Tasks

## 1. Rename Shared Room State

- Rename `coordinator/client/src/music.js` and its test to accurate room-state
  names.
- Preserve exports and behavior while updating imports and test descriptions.
- Keep state concrete; do not introduce a store library, context provider, or
  generalized event registry.

## 2. Extract Today And Music

- Move Today and its local-time helper into one channel component.
- Move Music artwork, progress, loaded, and empty presentation into one channel
  component.
- Preserve existing props, copy, classes, accessibility labels, and remote
  artwork safeguards.

## 3. Extract Shared Room Feedback

- Move connection, lighting, toast, identify, and scene feedback into one small
  shared presentation module.
- Keep action constants and lifecycle ownership explicit and avoid generic
  variant configuration.

## 4. Keep The Application Switch Explicit

- Leave `App.jsx` responsible for SSE, endpoint identity, action requests,
  keyboard listener lifecycle, and one hard-coded Today/Music render choice.
- Run the complete repository checks and create `docs/wip/GH-013.md` with the
  implementation walkthrough, plan diff, problems, and verification.

# Heatmap

Reference: `../project/HEATMAP.md`.

## Hot

### H1 - Separate Ownership Without A Channel Framework

- Decision: Extract concrete modules while retaining one explicit switch in
  `App.jsx`.
- Proposed approach: Use normal React components and named imports with no
  registry, router, dynamic loading, configuration, or plugin hooks.
- Why: Parallel issues need smaller ownership surfaces, but three known
  channels do not justify a permanent extension protocol.
- Alternatives: Keep the monolith; create a route per channel; define a dynamic
  channel manifest; split builds.
- Review focus: Whether the extraction is genuinely behavior-preserving and
  whether any abstraction exists only for hypothetical channels.

### H2 - Keep Shared Feedback Above Channels

- Decision: Connection, lighting, and action feedback remain shell-owned rather
  than becoming props repeated inside channel components.
- Proposed approach: Extract one shared feedback module rendered once by the
  shell after the active channel.
- Why: These states already span Today and Music and will also need to remain
  visible during voice and Headlines work.
- Alternatives: Duplicate feedback in every channel; let channels register
  overlays; leave all feedback implementation in `App.jsx`.
- Review focus: Layering, accessibility live regions, interaction
  serialization, and unchanged visible behavior.
