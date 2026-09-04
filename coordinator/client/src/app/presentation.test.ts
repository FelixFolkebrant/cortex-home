import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test, { after } from "node:test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer } from "vite";

const vite = await createServer({
  appType: "custom",
  server: { hmr: false, middlewareMode: true },
});
const { HomeSurface } = await vite.ssrLoadModule("/src/app/HomeSurface.tsx");
const { AlarmRuntime, requestAlarm, requestSleep } = await vite.ssrLoadModule(
  "/src/alarm/AlarmRuntime.tsx",
);
const { CameraMode } = await vite.ssrLoadModule("/src/camera/CameraMode.tsx");
const { MusicFullscreen, updateFullscreenTracks } = await vite.ssrLoadModule(
  "/src/music/MusicFullscreen.tsx",
);
const {
  isSystemStatsDismissShortcut,
  isSystemStatsShortcut,
  requestSystemStats,
  SystemStats,
} = await vite.ssrLoadModule("/src/diagnostics/SystemStats.tsx");
const { RoomFeedback } = await vite.ssrLoadModule("/src/voice/RoomFeedback.tsx");
const styles = readFileSync(new URL("./styles.css", import.meta.url), "utf8");

after(() => vite.close());

const playback = {
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
};

test("Home composes only current weather, an armed alarm, and now playing", () => {
  const markup = renderToStaticMarkup(
    createElement(HomeSurface, {
      alarm: { status: "armed", time: "07:00" },
      playback,
      summary: {
        status: "available",
        timeZone: "Europe/Stockholm",
        current: { condition: "clear", temperatureC: 18 },
        forecast: [{ condition: "rain", date: "Tomorrow", highC: 20, lowC: 10 }],
      },
    }),
  );

  assert.match(markup, /aria-label="Home"/);
  assert.match(markup, /18°/);
  assert.match(markup, /Alarm set for 07:00/);
  assert.match(markup, /The Track/);
  assert.match(markup, /The Artist/);
  assert.match(markup, /Artwork for The Track/);
  assert.match(markup, /width:65%/);
  assert.doesNotMatch(markup, /Tomorrow|Linköping|MET Norway|Cortex Home \/ Today/);
});

test("Home omits playback and alarm cards when neither is active", () => {
  const markup = renderToStaticMarkup(
    createElement(HomeSurface, {
      alarm: { status: "disarmed", time: null },
      playback: { status: "stopped", item: null },
      summary: {
        status: "unavailable",
        timeZone: "Europe/Stockholm",
        current: null,
        forecast: [],
      },
    }),
  );

  assert.match(markup, /Weather unavailable/);
  assert.doesNotMatch(markup, /Now playing|Alarm set for/);
});

test("Alarm runtime is nonvisual and preserves local ring audio control", async () => {
  assert.equal(
    renderToStaticMarkup(
      createElement(AlarmRuntime, {
        onDismiss: () => {},
        snapshot: { status: "ringing", time: "07:00" },
      }),
    ),
    "",
  );

  const calls = [];
  assert.equal(
    await requestAlarm("/alarm/start", async (url, options) => {
      calls.push({ options, url });
      return { ok: true, json: async () => ({ state: "playing" }) };
    }),
    "playing",
  );
  assert.deepEqual(calls, [
    {
      options: { method: "POST" },
      url: "http://127.0.0.1:38019/alarm/start",
    },
  ]);
});

test("Alarm sleep sends only the coordinator-resolved wake epoch", async () => {
  const calls = [];
  await requestSleep("2026-07-28T05:15:00Z", async (url, options) => {
    calls.push({ options, url });
    return { ok: true, json: async () => ({ state: "sleeping" }) };
  });
  assert.deepEqual(calls, [
    {
      options: { method: "POST" },
      url: "http://127.0.0.1:38019/alarm/sleep/1785215700",
    },
  ]);
});

test("Camera renders only a black-backed mirrored feed", () => {
  const markup = renderToStaticMarkup(createElement(CameraMode));

  assert.match(markup, /<video/);
  assert.match(markup, /autoPlay/);
  assert.match(markup, /muted/);
  assert.match(markup, /scale-x-\[-1\]/);
  assert.match(markup, /object-cover/);
  assert.match(markup, /bg-black/);
  assert.doesNotMatch(
    markup,
    /Opening|Camera unavailable|permission|ring light|local mirror ·|←|→/i,
  );
});

test("Music fullscreen uses only artwork and progress-filled title metadata", () => {
  const markup = renderToStaticMarkup(createElement(MusicFullscreen, { playback }));

  assert.match(markup, /Music fullscreen view/);
  assert.match(markup, /Artwork for The Track/);
  assert.match(markup, />The Track<\/h1>/);
  assert.match(markup, />The Artist<\/p>/);
  assert.match(markup, /--music-progress:65%/);
  assert.doesNotMatch(markup, /Spotify|Hidden Collection|Playback progress/);
});

test("Music fullscreen retains the previous track for its sharp left swipe", () => {
  const initial = updateFullscreenTracks(
    { current: null, outgoing: null, generation: 0 },
    playback,
  );
  const second = {
    ...playback,
    item: { ...playback.item, title: "Second Track", uri: "spotify:track:second" },
    positionMs: 0,
  };
  const changed = updateFullscreenTracks(initial, second);

  assert.equal(changed.current.item.title, "Second Track");
  assert.equal(changed.outgoing.item.title, "The Track");
  assert.equal(changed.generation, 1);
  assert.match(styles, /@keyframes music-track-enter/);
  assert.match(styles, /@keyframes music-track-exit/);
});

test("listening uses the small red sun and a centered level-driven black bar", () => {
  const markup = renderToStaticMarkup(
    createElement(RoomFeedback, {
      connection: "connected",
      interaction: {
        action: "speech.capture",
        level: 0.5,
        state: "user-speaking",
      },
      subtitle: "What will the weather be like today?",
    }),
  );

  assert.match(markup, /aria-label="Listening"/);
  assert.match(markup, /voice-listening/);
  assert.match(markup, /#ff7b00/);
  assert.match(markup, /transform:scale\(1.05\)/);
  assert.match(markup, /width:54%/);
  assert.match(markup, /bg-black/);
  assert.match(markup, /What will the weather be like today\?/);
  assert.doesNotMatch(markup, /Speak naturally|Hearing you|Microphone/);
});

test("agent speech uses the large yellow sun without the input bar", () => {
  const markup = renderToStaticMarkup(
    createElement(RoomFeedback, {
      connection: "connected",
      interaction: { action: "agent.interaction", level: 0, state: "speaking" },
    }),
  );

  assert.match(markup, /aria-label="Agent speaking"/);
  assert.match(markup, /size-\[clamp\(10\.5rem,13\.3vw,15\.4rem\)\]/);
  assert.match(markup, /voice-speaking/);
  assert.match(markup, /#ffb100/);
  assert.doesNotMatch(markup, /width:\d+%|Speaking\./);
});

test("voice-only feedback hides room chrome but keeps the agent sun", () => {
  const markup = renderToStaticMarkup(
    createElement(RoomFeedback, {
      connection: "disconnected",
      interaction: { action: "agent.interaction", state: "speaking" },
      voiceOnly: true,
    }),
  );

  assert.match(markup, /Agent speaking/);
  assert.doesNotMatch(markup, /Coordinator offline/);
});

test("voice diagnostics show only content-free timing and size metrics", () => {
  const markup = renderToStaticMarkup(
    createElement(RoomFeedback, {
      connection: "connected",
      interaction: { state: "idle" },
      voiceDebug: {
        answerBytes: 48_000,
        answerCharacters: 72,
        answerDurationMs: 2_000,
        llmMs: 1_234.5,
        phase: "completed",
        requestId: "must-not-render",
      },
      voiceDebugVisible: true,
    }),
  );

  assert.match(markup, /Voice diagnostics/);
  assert.match(markup, /1,235 ms/);
  assert.match(markup, /72 characters/);
  assert.doesNotMatch(markup, /must-not-render/);
});

test("system stats shortcuts and local validation remain unchanged", async () => {
  const shortcut = {
    altKey: true,
    code: "KeyM",
    ctrlKey: true,
    metaKey: false,
    repeat: false,
    shiftKey: false,
  };
  assert.equal(isSystemStatsShortcut(shortcut), true);
  assert.equal(
    isSystemStatsDismissShortcut({
      altKey: false,
      ctrlKey: false,
      key: "Escape",
      metaKey: false,
      repeat: false,
      shiftKey: false,
    }),
    true,
  );

  const stats = {
    cpuPercent: 12.5,
    loadOne: 0.3,
    memoryPercent: 44.2,
    memoryTotalMiB: 7900,
    memoryUsedMiB: 3492,
    temperatureC: 52.1,
    uptimeSeconds: 3720,
  };
  assert.deepEqual(
    await requestSystemStats(async () => ({ ok: true, json: async () => stats })),
    stats,
  );
  assert.match(
    renderToStaticMarkup(createElement(SystemStats, { visible: true })),
    /iMac performance/,
  );
});
