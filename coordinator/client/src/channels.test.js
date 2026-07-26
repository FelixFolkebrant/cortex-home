import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { after, test } from "node:test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer } from "vite";

const vite = await createServer({
  appType: "custom",
  server: { hmr: false, middlewareMode: true },
});
const { MusicChannel, MusicFullscreen, updateFullscreenTracks } =
  await vite.ssrLoadModule("/src/MusicChannel.jsx");
const { RoomFeedback } = await vite.ssrLoadModule("/src/RoomFeedback.jsx");
const { TodayChannel } = await vite.ssrLoadModule("/src/TodayChannel.jsx");
const styles = readFileSync(new URL("./styles.css", import.meta.url), "utf8");

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

  assert.match(markup, /Playback source:/);
  assert.match(markup, />Spotify</);
  assert.match(markup, /fill="#1ed760"/);
  assert.doesNotMatch(markup, /Cortex Home/);
  assert.doesNotMatch(markup, /Paused/);
  assert.doesNotMatch(markup, /Music|Episode/);
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

  assert.match(stopped, /Playback source:/);
  assert.match(stopped, />Spotify</);
  assert.match(
    stopped,
    /Choose &quot;Högtalaren&quot; as speaker in Spotify to connect/,
  );
  assert.doesNotMatch(stopped, /Cortex Home \/ Music/);
  assert.doesNotMatch(
    stopped,
    /Playback stopped|when the room needs music|Stopped|<p(?:\s|>)/,
  );
  assert.match(unavailable, /Receiver unavailable\./);
  assert.match(unavailable, /Högtalaren will report again/);
});

test("room feedback shows persistent lighting only when requested by Home", () => {
  const homeMarkup = renderToStaticMarkup(
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
      showLightingStatus: true,
    }),
  );
  const musicMarkup = renderToStaticMarkup(
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
      showLightingStatus: false,
    }),
  );

  assert.match(homeMarkup, /Coordinator offline · Reconnecting/);
  assert.match(homeMarkup, /Warm active/);
  assert.match(homeMarkup, /Changing view\./);
  assert.doesNotMatch(homeMarkup, /Cortex Home \/ Today/);
  assert.doesNotMatch(musicMarkup, /Warm active/);
  assert.match(musicMarkup, /Coordinator offline · Reconnecting/);
  assert.match(musicMarkup, /Changing view\./);
});

test("Music fullscreen uses only artwork and progress-filled title metadata", () => {
  const markup = renderToStaticMarkup(
    createElement(MusicFullscreen, {
      playback: {
        status: "paused",
        item: {
          artworkUrl: "https://example.test/cover.jpg",
          collection: "Hidden Collection",
          creators: ["The Artist"],
          durationMs: 100_000,
          title: "The Track",
          type: "track",
          uri: "spotify:track:current",
        },
        observedAt: "2026-07-26T12:00:00.000Z",
        positionMs: 65_000,
      },
    }),
  );

  assert.match(markup, /Music fullscreen view/);
  assert.match(markup, /Artwork for The Track/);
  assert.match(markup, /The Track/);
  assert.match(markup, /The Artist/);
  assert.match(markup, /--music-progress:65%/);
  assert.match(markup, /--music-unplayed:rgb\(255 255 255 \/ 60%\)/);
  assert.match(markup, /--music-artist:rgb\(255 255 255 \/ 40%\)/);
  assert.match(markup, /<h1[^>]*>The Track<\/h1><p>The Artist<\/p>/);
  assert.match(styles, /\.music-fullscreen-copy\s*\{[^}]*flex-direction:\s*column;/s);
  assert.doesNotMatch(markup, /Spotify|Hidden Collection|Playback progress|1:05|1:40/);
});

test("Music fullscreen shows the upcoming item only in the final ten seconds", () => {
  const playback = {
    status: "paused",
    item: {
      artworkUrl: "https://example.test/current.jpg",
      collection: "Current Collection",
      creators: ["Current Artist"],
      durationMs: 100_000,
      title: "Current Track",
      type: "track",
      uri: "spotify:track:current",
    },
    nextItem: {
      artworkUrl: "https://example.test/next.jpg",
      collection: "Next Collection",
      creators: ["Next Artist"],
      durationMs: 180_000,
      title: "Next Track",
      type: "track",
      uri: "spotify:track:next",
    },
    observedAt: "2026-07-26T12:00:00.000Z",
    positionMs: 89_999,
  };
  const before = renderToStaticMarkup(createElement(MusicFullscreen, { playback }));
  const during = renderToStaticMarkup(
    createElement(MusicFullscreen, {
      playback: { ...playback, positionMs: 92_000 },
    }),
  );

  assert.doesNotMatch(before, /Next Track|Next Artist/);
  assert.match(during, /Next Track/);
  assert.match(during, /Next Artist/);
  assert.match(during, /--music-progress:20%/);
  assert.match(during, /--music-accent:#ffffff/);
  assert.doesNotMatch(during, /Next Collection/);
});

test("Music fullscreen retains the previous track for a sharp 400ms left swipe", () => {
  const first = {
    status: "playing",
    item: {
      artworkUrl: "https://example.test/first.jpg",
      creators: ["First Artist"],
      durationMs: 100_000,
      title: "First Track",
      uri: "spotify:track:first",
    },
    positionMs: 99_000,
  };
  const second = {
    status: "playing",
    item: {
      artworkUrl: "https://example.test/second.jpg",
      creators: ["Second Artist"],
      durationMs: 120_000,
      title: "Second Track",
      uri: "spotify:track:second",
    },
    positionMs: 0,
  };
  const initial = updateFullscreenTracks(
    { current: null, outgoing: null, generation: 0 },
    first,
  );
  const retained = updateFullscreenTracks(initial, {
    status: "stopped",
    item: null,
    positionMs: 0,
  });
  const changed = updateFullscreenTracks(retained, second);

  assert.strictEqual(retained, initial);
  assert.equal(changed.current.item.title, "Second Track");
  assert.equal(changed.outgoing.item.title, "First Track");
  assert.equal(changed.generation, 1);
  assert.match(styles, /music-track-enter 400ms cubic-bezier\(0\.7, 0, 0\.3, 1\)/);
  assert.match(styles, /music-track-exit 400ms cubic-bezier\(0\.7, 0, 0\.3, 1\)/);
  assert.match(styles, /background-color 400ms cubic-bezier\(0\.7, 0, 0\.3, 1\)/);
});

test("room feedback makes deliberate microphone capture visible", () => {
  const markup = renderToStaticMarkup(
    createElement(RoomFeedback, {
      connection: "connected",
      lighting: { activeScenes: [], status: "available" },
      interaction: {
        action: "speech.capture",
        level: 0.5,
        message: null,
        scene: null,
        state: "listening",
      },
    }),
  );

  assert.match(markup, /Cortex Home \/ Microphone/);
  assert.match(markup, /Listening\./);
  assert.match(markup, /Keep holding Control, Alt, and Space\./);
  assert.match(markup, /width:55%/);
});

test("Music fullscreen keeps microphone feedback without room chrome", () => {
  const markup = renderToStaticMarkup(
    createElement(RoomFeedback, {
      connection: "disconnected",
      interaction: {
        action: "speech.capture",
        level: 0.5,
        message: null,
        scene: null,
        state: "listening",
      },
      lighting: {
        activeScenes: ["Warm"],
        status: "available",
      },
      showLightingStatus: true,
      voiceOnly: true,
    }),
  );

  assert.match(markup, /Cortex Home \/ Microphone/);
  assert.doesNotMatch(markup, /Coordinator offline · Reconnecting/);
  assert.doesNotMatch(markup, /Warm active/);
});
