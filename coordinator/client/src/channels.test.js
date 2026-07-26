import assert from "node:assert/strict";
import { after, test } from "node:test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer } from "vite";

const vite = await createServer({
  appType: "custom",
  server: { middlewareMode: true },
});
const { MusicChannel } = await vite.ssrLoadModule("/src/MusicChannel.jsx");
const { RoomFeedback } = await vite.ssrLoadModule("/src/RoomFeedback.jsx");
const { TodayChannel } = await vite.ssrLoadModule("/src/TodayChannel.jsx");

after(() => vite.close());

test("Today channel owns available weather and attribution presentation", () => {
  const markup = renderToStaticMarkup(
    createElement(TodayChannel, {
      summary: {
        status: "available",
        timeZone: "Europe/Stockholm",
        current: { condition: "clear", temperatureC: 20 },
        forecast: [
          {
            condition: "rain",
            date: "2026-07-27",
            highC: 18,
            lowC: 12,
          },
        ],
      },
    }),
  );

  assert.match(markup, /Cortex Home \/ Today/);
  assert.match(markup, /20°/);
  assert.match(markup, /Clear/);
  assert.match(markup, /Weather data: MET Norway · CC BY 4.0/);
});

test("Music channel owns loaded playback and artwork fallback presentation", () => {
  const markup = renderToStaticMarkup(
    createElement(MusicChannel, {
      connection: "connected",
      playback: {
        status: "paused",
        item: {
          artworkUrl: "http://example.test/cover.jpg",
          collection: "The Collection",
          creators: ["The Artist"],
          durationMs: 240_000,
          title: "The Track",
          type: "track",
        },
        observedAt: "2026-07-26T12:00:00.000Z",
        positionMs: 65_000,
      },
    }),
  );

  assert.match(markup, /Paused/);
  assert.match(markup, /The Track/);
  assert.match(markup, /The Artist/);
  assert.match(markup, /Artwork unavailable for The Track/);
  assert.match(markup, /1:05/);
});

test("Music channel owns stopped and unavailable presentation", () => {
  const stopped = renderToStaticMarkup(
    createElement(MusicChannel, {
      connection: "connected",
      playback: { status: "stopped", item: null },
    }),
  );
  const unavailable = renderToStaticMarkup(
    createElement(MusicChannel, {
      connection: "connected",
      playback: { status: "unavailable", item: null },
    }),
  );

  assert.match(stopped, /Playback stopped\./);
  assert.match(stopped, /Choose Högtalaren in Spotify/);
  assert.match(unavailable, /Receiver unavailable\./);
  assert.match(unavailable, /Högtalaren will report again/);
});

test("room feedback stays independent from channel presentation", () => {
  const markup = renderToStaticMarkup(
    createElement(RoomFeedback, {
      connection: "disconnected",
      lighting: {
        activeScenes: ["Warm"],
        status: "available",
      },
      interaction: {
        action: "channel.select",
        message: null,
        scene: null,
        state: "working",
      },
    }),
  );

  assert.match(markup, /Coordinator offline · Reconnecting/);
  assert.match(markup, /Warm active/);
  assert.match(markup, /Changing view\./);
  assert.doesNotMatch(markup, /Cortex Home \/ Today/);
  assert.doesNotMatch(markup, /Cortex Home \/ Music/);
});
