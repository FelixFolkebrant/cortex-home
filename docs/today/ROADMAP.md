# Today Roadmap

## Current

- [TOD-001](issues/TOD-001.md) adds coordinator-owned Today state, fixed
  Linköping weather through yr.no, local time and date, a three-day forecast,
  attribution, and an explicit unavailable state.
- Today is the startup channel and remains independent of Music, Lighting, and
  interaction feedback.

## Next

- Complete any remaining real-endpoint review of provider failure, narrow
  layouts, and reduced-motion presentation when that evidence is useful.
- Improve the dashboard only in response to an actual morning-glance need.

## Later

- Additional glanceable information such as photos, quotes, stocks, or calendar
  context only after its data source and privacy boundary are accepted.

## Open Decisions

- Whether Today should remain a single composition or eventually contain a
  small number of fixed sections.

## Accepted Decisions

- Use yr.no Locationforecast 2.0 from the ThinkPad with required attribution,
  expiry-aware caching, and fixed Linköping coordinates.
- Keep a small normalized client contract and a clear unavailable state.
- Keep Today as an explicit channel rather than a configurable dashboard.
