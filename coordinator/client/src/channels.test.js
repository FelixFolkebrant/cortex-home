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
const { AirPlayChannel, AirPlayStatus, isAirPlayToggleShortcut, requestAirPlay } =
  await vite.ssrLoadModule("/src/AirPlayChannel.jsx");
const { RoomFeedback } = await vite.ssrLoadModule("/src/RoomFeedback.jsx");
const {
  isSystemStatsDismissShortcut,
  isSystemStatsShortcut,
  requestSystemStats,
  SystemStats,
} = await vite.ssrLoadModule("/src/SystemStats.jsx");
const { TodayChannel } = await vite.ssrLoadModule("/src/TodayChannel.jsx");
const { CameraChannel, cameraStatusCopy } = await vite.ssrLoadModule(
  "/src/CameraChannel.jsx",
);
const { AlarmChannel, requestAlarm, requestAlarmFiles, requestSleep, selectAlarmFile } =
  await vite.ssrLoadModule("/src/AlarmChannel.jsx");
const styles = readFileSync(new URL("./styles.css", import.meta.url), "utf8");

after(() => vite.close());

test("AirPlay channel is only a logo, switch, and conditional status region", () => {
  const markup = renderToStaticMarkup(createElement(AirPlayChannel));

  assert.match(markup, />AirPlay</);
  assert.match(markup, /role="switch"/);
  assert.match(markup, /aria-checked="false"/);
  assert.match(markup, /aria-keyshortcuts="Enter"/);
  assert.match(markup, /min-h-screen/);
  assert.doesNotMatch(markup, /absolute inset-0/);
  assert.doesNotMatch(markup, /Ready to mirror|No code required|Ctrl/);
  assert.doesNotMatch(markup, /Select|Skärmen|PIN|password/i);
});

test("Alarm sleep sends only the coordinator-resolved wake epoch", async () => {
  const calls = [];
  await requestSleep("2026-07-28T05:15:00Z", async (url, options) => {
    calls.push({ url, options });
    return { ok: true, json: async () => ({ state: "sleeping" }) };
  });

  assert.deepEqual(calls, [
    {
      url: "http://127.0.0.1:38019/alarm/sleep/1785215700",
      options: { method: "POST" },
    },
  ]);
});

test("AirPlay shows only a loader while starting and Skärmen when on", () => {
  const starting = renderToStaticMarkup(
    createElement(AirPlayStatus, { state: "starting" }),
  );
  const on = renderToStaticMarkup(createElement(AirPlayStatus, { state: "on" }));

  assert.match(starting, /Starting AirPlay/);
  assert.doesNotMatch(starting, /Select|Skärmen/);
  assert.match(on, /Select/);
  assert.match(on, /Apple TV/);
  assert.match(on, /Skärmen/);
  assert.match(on, /to cast screen/);
});

test("AirPlay control uses the loopback bridge and validates its state", async () => {
  const calls = [];
  const state = await requestAirPlay("/on", async (url, options) => {
    calls.push({ url, options });
    return {
      ok: true,
      json: async () => ({ state: "on" }),
    };
  });

  assert.equal(state, "on");
  assert.deepEqual(calls, [
    {
      url: "http://127.0.0.1:38019/on",
      options: { method: "POST" },
    },
  ]);
  await assert.rejects(
    requestAirPlay("/status", async () => ({
      ok: true,
      json: async () => ({ state: "starting" }),
    })),
    /invalid state/,
  );
});

test("AirPlay retries the one-shot listener gap and hides raw fetch errors", async () => {
  let attempts = 0;
  const waits = [];
  const state = await requestAirPlay(
    "/status",
    async () => {
      attempts += 1;
      if (attempts === 1) {
        throw new TypeError("Failed to fetch");
      }
      return {
        ok: true,
        json: async () => ({ state: "off" }),
      };
    },
    async (duration) => waits.push(duration),
  );

  assert.equal(state, "off");
  assert.equal(attempts, 2);
  assert.deepEqual(waits, [75]);
  await assert.rejects(
    requestAirPlay(
      "/status",
      async () => {
        throw new TypeError("Failed to fetch");
      },
      async () => {},
    ),
    /AirPlay control is unavailable/,
  );
});

test("plain non-repeating Enter is the AirPlay toggle shortcut", () => {
  const enter = {
    key: "Enter",
    altKey: false,
    ctrlKey: false,
    metaKey: false,
    shiftKey: false,
    repeat: false,
  };

  assert.equal(isAirPlayToggleShortcut(enter), true);
  assert.equal(isAirPlayToggleShortcut({ ...enter, repeat: true }), false);
  assert.equal(isAirPlayToggleShortcut({ ...enter, ctrlKey: true }), false);
  assert.equal(isAirPlayToggleShortcut({ ...enter, key: " " }), false);
});

test("only exact Ctrl+Alt+M toggles the computer overview", () => {
  const shortcut = {
    altKey: true,
    code: "KeyM",
    ctrlKey: true,
    metaKey: false,
    repeat: false,
    shiftKey: false,
  };

  assert.equal(isSystemStatsShortcut(shortcut), true);
  for (const changed of [
    { altKey: false },
    { code: "KeyS" },
    { ctrlKey: false },
    { metaKey: true },
    { repeat: true },
    { shiftKey: true },
  ]) {
    assert.equal(isSystemStatsShortcut({ ...shortcut, ...changed }), false);
  }
});

test("only plain non-repeating Escape closes the computer overview", () => {
  const shortcut = {
    altKey: false,
    ctrlKey: false,
    key: "Escape",
    metaKey: false,
    repeat: false,
    shiftKey: false,
  };

  assert.equal(isSystemStatsDismissShortcut(shortcut), true);
  for (const changed of [
    { altKey: true },
    { ctrlKey: true },
    { key: "KeyM" },
    { metaKey: true },
    { repeat: true },
    { shiftKey: true },
  ]) {
    assert.equal(isSystemStatsDismissShortcut({ ...shortcut, ...changed }), false);
  }
});

test("computer overview validates local endpoint stats", async () => {
  const stats = {
    cpuPercent: 12.5,
    loadOne: 0.3,
    memoryPercent: 44.2,
    memoryTotalMiB: 7900,
    memoryUsedMiB: 3492,
    temperatureC: 52.1,
    uptimeSeconds: 3720,
  };
  const calls = [];

  assert.deepEqual(
    await requestSystemStats(async (url) => {
      calls.push(url);
      return { ok: true, json: async () => stats };
    }),
    stats,
  );
  assert.deepEqual(calls, ["http://127.0.0.1:38019/stats"]);
  let attempts = 0;
  const waits = [];
  assert.deepEqual(
    await requestSystemStats(
      async () => {
        attempts += 1;
        if (attempts === 1) {
          throw new TypeError("Failed to fetch");
        }
        return { ok: true, json: async () => stats };
      },
      async (duration) => waits.push(duration),
    ),
    stats,
  );
  assert.equal(attempts, 2);
  assert.deepEqual(waits, [75]);
  await assert.rejects(
    requestSystemStats(
      async () => {
        throw new TypeError("Failed to fetch");
      },
      async () => {},
    ),
    /Computer stats are unavailable/,
  );
  await assert.rejects(
    requestSystemStats(async () => ({
      ok: true,
      json: async () => ({ ...stats, cpuPercent: 101 }),
    })),
    /invalid data/,
  );
});

test("computer overview is global, compact, and content-free", () => {
  const hidden = renderToStaticMarkup(createElement(SystemStats, { visible: false }));
  const visible = renderToStaticMarkup(createElement(SystemStats, { visible: true }));

  assert.equal(hidden, "");
  assert.match(visible, /Computer performance overview/);
  assert.match(visible, /iMac performance/);
  assert.match(visible, /Close computer overview/);
  assert.match(visible, /Close · Esc/);
  assert.match(visible, /Collecting local computer stats/);
  assert.doesNotMatch(visible, /backdrop-blur/);
});

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

test("Ringing Alarm replaces the editor with a dominant live clock", () => {
  const markup = renderToStaticMarkup(
    createElement(AlarmChannel, {
      onAction: () => {},
      snapshot: { status: "ringing", time: "07:30", firesAt: null },
    }),
  );

  assert.match(markup, /aria-label="Ringing alarm"/);
  assert.match(markup, /Press Enter to dismiss/);
  assert.doesNotMatch(markup, /Press Ctrl\+Enter to sleep/);
});

test("Alarm audio calls only the loopback start and stop routes", async () => {
  const calls = [];
  const state = await requestAlarm("/alarm/start", async (url, options) => {
    calls.push({ url, options });
    return { ok: true, json: async () => ({ state: "playing" }) };
  });

  assert.equal(state, "playing");
  assert.deepEqual(calls, [
    {
      url: "http://127.0.0.1:38019/alarm/start",
      options: { method: "POST" },
    },
  ]);
  await assert.rejects(
    requestAlarm("/alarm/stop", async () => ({
      ok: true,
      json: async () => ({ state: "unknown" }),
    })),
    /Alarm audio is unavailable/,
  );
});

test("Alarm sound selector lists and applies only endpoint catalog entries", async () => {
  const calls = [];
  const files = await requestAlarmFiles(async (url, options) => {
    calls.push({ url, options });
    return {
      ok: true,
      json: async () => ({
        files: ["birds.mp3", "wake-alarm.mp3"],
        selected: "birds.mp3",
      }),
    };
  });
  await selectAlarmFile("wake-alarm.mp3", async (url, options) => {
    calls.push({ url, options });
    return { ok: true, json: async () => ({ state: "selected" }) };
  });

  assert.deepEqual(files, {
    files: ["birds.mp3", "wake-alarm.mp3"],
    selected: "birds.mp3",
  });
  assert.deepEqual(calls, [
    {
      url: "http://127.0.0.1:38019/alarm/files",
      options: { method: "GET" },
    },
    {
      url: "http://127.0.0.1:38019/alarm/select/wake-alarm.mp3",
      options: { method: "POST" },
    },
  ]);
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

test("Camera channel is unmistakably local before capture starts", () => {
  const markup = renderToStaticMarkup(createElement(CameraChannel));

  assert.match(markup, /Cortex Home \/ Camera/);
  assert.match(markup, /Opening the local camera\./);
  assert.match(markup, /Camera/);
  assert.match(markup, /Local mirror · Video stays on this iMac/);
  assert.match(markup, /Ring light off/);
  assert.match(markup, /← \/ → light · ↑ \/ ↓ width/);
  assert.match(markup, /autoPlay/);
  assert.match(markup, /muted/);
  assert.match(markup, /scale-x-\[-1\]/);
  assert.match(markup, /object-cover/);
  assert.doesNotMatch(markup, /controls/);
  assert.match(
    styles,
    /\.camera-ring-light::after\s*\{[^}]*inset:\s*calc\(var\(--camera-ring-width\) \/ 2\)[^}]*border-radius:[^}]*box-shadow:\s*0 0 0 100vmax[^}]*inset 0 0/s,
  );
  assert.doesNotMatch(styles, /\.camera-ring-light\s*\{[^}]*border-radius/s);
});

test("Camera channel defines explicit recoverable failure presentation", () => {
  assert.deepEqual(Object.keys(cameraStatusCopy).sort(), [
    "blocked",
    "denied",
    "ended",
    "starting",
    "unavailable",
    "unsupported",
  ]);
  assert.match(cameraStatusCopy.blocked.join(" "), /origin/);
  assert.match(cameraStatusCopy.denied.join(" "), /permission denied/i);
  assert.match(cameraStatusCopy.ended.join(" "), /leave Camera and return/i);
  assert.match(cameraStatusCopy.unavailable.join(" "), /missing, busy/);
  assert.match(cameraStatusCopy.unsupported.join(" "), /isn’t supported/);
});

test("room feedback shows persistent lighting only when requested by a channel", () => {
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

test("room feedback keeps contextual answer phases compact and content-free", () => {
  for (const [state, title] of [
    ["transcribing", "Transcribing."],
    ["thinking", "Thinking."],
    ["speaking", "Speaking."],
    ["completed", "Answered."],
    ["failed", "Couldn’t answer."],
  ]) {
    const markup = renderToStaticMarkup(
      createElement(RoomFeedback, {
        connection: "connected",
        interaction: {
          action: "agent.interaction",
          message: null,
          state,
        },
        lighting: { activeScenes: [], status: "available" },
      }),
    );

    assert.match(markup, /Cortex Home \/ Voice answer/);
    assert.match(markup, new RegExp(title.replace(".", "\\.")));
    assert.doesNotMatch(markup, /transcript|requestId|answer text/i);
  }
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

test("Music fullscreen keeps contextual answer feedback without room chrome", () => {
  const markup = renderToStaticMarkup(
    createElement(RoomFeedback, {
      connection: "disconnected",
      interaction: {
        action: "agent.interaction",
        message: null,
        state: "speaking",
      },
      lighting: {
        activeScenes: ["Warm"],
        status: "available",
      },
      showLightingStatus: true,
      voiceOnly: true,
    }),
  );

  assert.match(markup, /Cortex Home \/ Voice answer/);
  assert.match(markup, /Speaking\./);
  assert.doesNotMatch(markup, /Coordinator offline · Reconnecting/);
  assert.doesNotMatch(markup, /Warm active/);
});

test("voice diagnostics show only content-free timing and size metrics", () => {
  const debug = {
    answerBytes: 48_000,
    answerCharacters: 72,
    answerDurationMs: 2_000,
    answerTransferMs: 6.4,
    captureBytes: 64_044,
    captureDurationMs: 2_000,
    llmMs: 1_234.5,
    phase: "completed",
    playbackMs: 2_010,
    requestId: "must-not-render",
    sttMs: 345.6,
    totalToAudioMs: 1_800,
    transcriptCharacters: 31,
    ttsMs: 210.2,
    uploadMs: 4.2,
  };
  const hidden = renderToStaticMarkup(
    createElement(RoomFeedback, {
      connection: "connected",
      interaction: { state: "idle" },
      lighting: null,
      voiceDebug: debug,
      voiceDebugVisible: false,
    }),
  );
  const visible = renderToStaticMarkup(
    createElement(RoomFeedback, {
      connection: "connected",
      interaction: { state: "idle" },
      lighting: null,
      voiceDebug: debug,
      voiceDebugVisible: true,
      voiceOnly: true,
    }),
  );

  assert.doesNotMatch(hidden, /Voice diagnostics/);
  assert.match(visible, /Voice diagnostics/);
  assert.match(visible, /LLM round trip/);
  assert.match(visible, /1,235 ms/);
  assert.match(visible, /2\.00 s · 62\.5 KiB/);
  assert.match(visible, /72 characters/);
  assert.doesNotMatch(visible, /must-not-render/);
  assert.doesNotMatch(visible, /Coordinator offline|Scenes unavailable/);
});
