# PP-5: Independent Channel Evolution

## Slice

Today and Music become explicit channel modules, receive one focused visual
polish pass, and are joined by a read-only Headlines channel without blocking
or depending on the concurrent voice-agent work.

- The full-screen React shell retains one coordinator connection, shared room
  feedback, and explicit channel selection.
- Today and Music move into separate components without changing their state
  contracts or behavior.
- Shared room state, keyboard classification, and feedback use names that no
  longer imply they belong only to Music.
- A new Headlines channel shows a small current selection from the exact BBC
  World RSS feed with clear source attribution and failure state.
- `Ctrl`+`Alt`+`3` selects Headlines through the same `channel.select` action.
- Channel work uses issue worktrees with independent documentation checkouts;
  deployment to the shared physical room remains serialized.

This is the smallest useful channel-expansion slice because a third real
channel proves which presentation seams repeat while an external read-only feed
proves the next coordinator adapter without inventing a plugin framework.

## Out Of Scope

- A router, browser history, deep links, dynamic channel discovery, a plugin
  API, configurable dashboards, widgets, or user-managed channel ordering.
- Mouse, touchscreen, on-screen channel controls, configurable shortcuts, or
  more than the three fixed channel shortcuts.
- Full article bodies, article scraping, AI summaries, recommendation ranking,
  personalization, search, bookmarks, read state, or opening links from the
  kiosk.
- Multiple news providers, configurable feeds, local news, breaking-news
  alerts, audio news playback, or durable article history.
- Changing Today's weather provider, Spotify playback integration, Hue state,
  or existing coordinator action semantics.
- Making Headlines available to the voice agent in this slice.
- Sharing a mutable `docs/`, dependency, build, or deployment directory across
  worktrees.

## Deferred To Later Planpoints

- Agent-aware Headlines context remains deferred until both independent slices
  are merged and the desired copyright and context boundary can be reviewed
  against a concrete display.
- Additional channels remain one useful slice at a time so Photos, stocks,
  local media, and TV do not force a common interface before their data and
  interaction needs are known.
- A channel registry or plugin protocol remains deferred until explicit wiring
  for at least three channels produces repeated code that a smaller local
  abstraction cannot remove.
- Configurable sources remain deferred because one exact feed is sufficient to
  prove normalized headline state and recovery.

## Crossroads

### C1 - Channel Module Boundary

- Decision: How independent channel work avoids repeatedly editing the complete
  application shell.
- Options: Keep every view in `App.jsx`; extract explicit channel components;
  add a router; build a dynamic registry or plugin API; split channels into
  separate applications.
- Impact if wrong: Parallel channel work could create permanent merge hotspots,
  while a premature extension framework would define contracts before channel
  needs are known.
- Proposed choice: Extract explicit Today and Music components plus shared room
  state and feedback modules. Keep one small hard-coded channel switch in the
  application shell and add Headlines explicitly when its real contract exists.
- Why: Three known channels justify file ownership and accurate names, but not
  runtime discovery, routing, configuration, or separate deployments.
- Status: decided

### C2 - First New Channel And Data Source

- Decision: Which concrete channel proves the next module and provider boundary.
- Options: BBC World headlines through RSS; Sveriges Radio's unmaintained Open
  API; local photos; quotes; stocks; local media; TV.
- Impact if wrong: The first parallel channel could introduce accounts,
  licensing ambiguity, hardware, media playback, or configuration that obscures
  whether the channel boundary itself works.
- Proposed choice: Add a Headlines channel backed only by
  `https://feeds.bbci.co.uk/news/world/rss.xml`. Show a bounded set of exact
  titles, descriptions, and publication times with prominent BBC attribution
  and no rewriting or article-body fetch.
- Why: The feed is live, stable, read-only, account-free, and explicitly
  intended for personal RSS use with attribution. Sveriges Radio's official API
  remains usable but is no longer maintained; the other candidates need
  personal content, accounts, market-data policy, or media decisions.
- Status: decided

### C3 - Parallel Worktree And Documentation Ownership

- Decision: Whether concurrent issue branches share checked-out documentation
  or keep branch-local copies.
- Options: Symlink one shared `docs/`; keep separate worktree checkouts; create
  a documentation repository; let each branch allocate its own issue numbers.
- Impact if wrong: Shared files can change behind another worktree's index, and
  independent number allocation can create colliding issue records.
- Proposed choice: Reserve all issue numbers in the accepted Planpoints on
  `main`. Give every issue worktree its complete normal `docs/` checkout. Limit
  issue branches to their own WIP records and rebase shared planning changes
  from `main`.
- Why: Worktrees already share Git objects and refs. Checked-out files and
  indexes must remain independent for Git to report and merge changes
  correctly.
- Status: decided

## Plumbing

- Threaded first: the existing `channel.active`, `today.summary`,
  `music.playback`, `room.lighting`, and action feedback contracts move behind
  explicit frontend module boundaries without changing their payloads.
- Threaded next: `news.headlines` carries exact availability, source, feed
  update time, and a bounded ordered list of title, description, publication
  time, and canonical link values.
- Action boundary: `channel.select` adds only `headlines`, and
  `Ctrl`+`Alt`+`3` submits that exact value through the existing request
  lifecycle.
- Provider boundary: only the ThinkPad fetches and parses RSS. Chromium receives
  normalized text and never contacts BBC or loads remote article images.
- Recovery boundary: an invalid or expired feed produces explicit Headlines
  unavailability without affecting Today, Music, Hue, voice, or coordinator
  health.
- Pattern set: each channel owns one explicit normalized state adapter and one
  explicit view while the application shell owns connection, selection, and
  shared room feedback.

## Issues

1. **GH-013 - Separate The Channel Shell**: extract Today, Music, room state,
   keyboard classification, and shared feedback into accurately named frontend
   modules without visual, contract, dependency, or behavior changes.
2. **GH-015 - Polish Today And Music**: review both real channel views, improve
   their shared hierarchy and narrow-screen behavior, and keep every existing
   loading, empty, playback, weather, lighting, and feedback state.
3. **GH-017 - Present BBC World Headlines**: add one standard-library RSS
   adapter, normalized `news.headlines` snapshots, explicit Headlines view,
   fixed third shortcut, attribution, bounded caching, and independent failure
   recovery.

## Conceptual Heatmap

Reference: `../project/HEATMAP.md`.

### Crossroads

- C1: channel module boundary; see Crossroads section.
- C2: first new channel and data source; see Crossroads section.
- C3: parallel worktree and documentation ownership; see Crossroads section.

### Hot

#### H1 - Separate Files Without Inventing Extensions

- Decision: Give real channels independent files and tests while retaining one
  explicit application switch.
- Why: File ownership reduces merge conflicts; a runtime registry would add a
  broader product contract than three channels require.
- Alternatives: Keep the monolith; build a plugin API; split deployments.

#### H2 - Normalize Headlines At The Coordinator

- Decision: Parse and validate the exact RSS feed on the ThinkPad and publish
  only a small stable snapshot to the endpoint.
- Why: Browser-to-provider access would split credentials, failure behavior,
  caching, and future agent context from the accepted coordinator boundary.
- Alternatives: Fetch RSS in Chromium; scrape article pages; forward raw XML;
  ask a model to generate a digest.

#### H3 - Keep Concurrent Integration Serialized

- Decision: Code and test in parallel issue worktrees, but merge frequently and
  deploy only one integrated branch to the physical room at a time.
- Why: Git can isolate source work, while the ThinkPad, iMac, microphone, Hue
  bridge, and Sonos are one shared environment.
- Alternatives: Long-lived integration branches; simultaneous deployments;
  separate repositories or duplicated environments.

## References

- BBC RSS feed: `https://feeds.bbci.co.uk/news/world/rss.xml`
- BBC RSS terms:
  `https://www.bbc.co.uk/usingthebbc/terms-of-use/#15metadataandrssfeeds`
- Sveriges Radio Open API status:
  `https://www.sverigesradio.se/oppetapi`
