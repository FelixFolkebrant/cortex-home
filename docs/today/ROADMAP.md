# Today Roadmap

## Current

- [TOD-001](issues/TOD-001.md) adds coordinator-owned Today state, fixed
  Linköping weather through yr.no, local time and date, a three-day forecast,
  attribution, and an explicit unavailable state.
- Home currently presents only the local clock, abbreviated date, and current
  temperature over the weather image. The normalized forecast and attribution
  remain available to the coordinator but are intentionally hidden.

## Next

- Complete any remaining real-endpoint review of provider failure, narrow
  layouts, and reduced-motion presentation when that evidence is useful.
- Improve the Home region only in response to an actual morning-glance need.

## Later

- Additional glanceable information such as photos, quotes, stocks, or calendar
  context only after its data source and privacy boundary are accepted.

## Open Decisions

- Whether a later summoned weather detail should reuse the retained normalized
  forecast.

## Accepted Decisions

- Use yr.no Locationforecast 2.0 from the ThinkPad with required attribution,
  expiry-aware caching, and fixed Linköping coordinates.
- Keep a small normalized client contract and a clear unavailable state.
- Keep current weather as one explicit Home region rather than a configurable
  dashboard.
