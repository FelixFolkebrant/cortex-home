import assert from "node:assert/strict";
import test from "node:test";
import {
  artworkSource,
  formatTime,
  initialRoomState,
  keyboardAction,
  nextScene,
  projectPosition,
  roomReducer,
} from "./room-state.js";

const item = {
  artworkUrl: "https://example.test/cover.jpg",
  durationMs: 240_000,
};

const playing = {
  status: "playing",
  item,
  positionMs: 30_000,
  observedAt: "2026-07-25T12:00:00.000Z",
};

test("connection and interaction events preserve playback", () => {
  const withPlayback = roomReducer(initialRoomState, {
    type: "playback",
    snapshot: playing,
  });
  const disconnected = roomReducer(withPlayback, {
    type: "connection",
    state: "disconnected",
  });
  const identifying = roomReducer(disconnected, {
    type: "interaction",
    state: "identifying",
  });

  assert.equal(identifying.playback, playing);
  assert.equal(identifying.connection, "disconnected");
  assert.equal(identifying.interaction.state, "identifying");
  assert.equal(identifying.interaction.action, null);
});

test("lighting and scene interaction events remain independent", () => {
  const lighting = {
    scene: "Warm",
    status: "active",
    observedAt: "2026-07-26T12:00:00.000Z",
  };
  const withLighting = roomReducer(initialRoomState, {
    type: "lighting",
    snapshot: lighting,
  });
  const working = roomReducer(withLighting, {
    type: "interaction",
    action: "room.scene.activate",
    state: "working",
  });
  const withPlayback = roomReducer(working, {
    type: "playback",
    snapshot: playing,
  });

  assert.equal(withPlayback.lighting, lighting);
  assert.equal(withPlayback.playback, playing);
  assert.deepEqual(withPlayback.interaction, {
    state: "working",
    action: "room.scene.activate",
    message: null,
    scene: null,
  });
});

test("channel and Today updates preserve Music and room feedback", () => {
  const today = {
    status: "available",
    timeZone: "Europe/Stockholm",
    current: { condition: "clear", temperatureC: 20 },
    forecast: [],
  };
  const withPlayback = roomReducer(initialRoomState, {
    type: "playback",
    snapshot: playing,
  });
  const withLighting = roomReducer(withPlayback, {
    type: "lighting",
    snapshot: { scene: "Warm", status: "active" },
  });
  const withToday = roomReducer(withLighting, { type: "today", snapshot: today });
  const result = roomReducer(withToday, {
    type: "channel",
    snapshot: { active: "today" },
  });

  assert.equal(result.playback, playing);
  assert.equal(result.lighting.status, "active");
  assert.equal(result.today, today);
  assert.equal(result.channel.active, "today");
});

test("a terminal snapshot replaces loaded playback", () => {
  const withPlayback = roomReducer(initialRoomState, {
    type: "playback",
    snapshot: playing,
  });
  const stopped = {
    status: "stopped",
    item: null,
    positionMs: 0,
    observedAt: "2026-07-25T12:01:00.000Z",
  };

  const result = roomReducer(withPlayback, {
    type: "playback",
    snapshot: stopped,
  });

  assert.equal(result.playback, stopped);
  assert.equal(result.playback.item, null);
});

test("playing progress advances and stays within duration", () => {
  assert.equal(projectPosition(playing, Date.parse(playing.observedAt) + 5000), 35_000);
  assert.equal(projectPosition(playing, Date.parse(playing.observedAt) - 5000), 30_000);
  assert.equal(
    projectPosition(playing, Date.parse(playing.observedAt) + 999_000),
    240_000,
  );
});

test("paused progress remains fixed and malformed values are bounded", () => {
  assert.equal(
    projectPosition(
      {
        ...playing,
        status: "paused",
        positionMs: 45_000,
      },
      Date.parse(playing.observedAt) + 30_000,
    ),
    45_000,
  );
  assert.equal(
    projectPosition({ ...playing, positionMs: -10 }, Date.parse(playing.observedAt)),
    0,
  );
  assert.equal(projectPosition({ ...playing, item: null }), 0);
});

test("artwork uses only valid HTTPS sources", () => {
  assert.equal(artworkSource(item), "https://example.test/cover.jpg");
  assert.equal(artworkSource({ artworkUrl: "http://example.test/cover.jpg" }), null);
  assert.equal(artworkSource({ artworkUrl: "not a url" }), null);
  assert.equal(artworkSource(null), null);
});

test("time formatting supports tracks and long episodes", () => {
  assert.equal(formatTime(0), "0:00");
  assert.equal(formatTime(65_900), "1:05");
  assert.equal(formatTime(3_661_000), "1:01:01");
});

test("only fixed Ctrl+Alt channel shortcuts are accepted", () => {
  const keyboardEvent = {
    altKey: true,
    code: "Digit1",
    ctrlKey: true,
    metaKey: false,
    repeat: false,
    shiftKey: false,
  };

  assert.deepEqual(keyboardAction(keyboardEvent), {
    action: "channel.select",
    channel: "today",
  });
  assert.deepEqual(keyboardAction({ ...keyboardEvent, code: "Digit2" }), {
    action: "channel.select",
    channel: "music",
  });
  assert.equal(keyboardAction({ ...keyboardEvent, code: "Digit3" }), null);
  assert.equal(keyboardAction({ ...keyboardEvent, repeat: true }), null);
  assert.equal(keyboardAction({ ...keyboardEvent, shiftKey: true }), null);
  assert.equal(keyboardAction({ ...keyboardEvent, metaKey: true }), null);
});

test("scene cycling follows the catalog and wraps", () => {
  const lighting = {
    status: "available",
    scenes: ["Bright", "Relax", "Warm"],
    activeScenes: ["Relax"],
  };

  assert.equal(nextScene(lighting), "Warm");
  assert.equal(nextScene({ ...lighting, activeScenes: ["Warm"] }), "Bright");
  assert.equal(nextScene({ ...lighting, activeScenes: [] }), "Bright");
  assert.equal(nextScene({ ...lighting, activeScenes: ["Bright", "Relax"] }), "Bright");
  assert.equal(nextScene({ status: "unavailable", scenes: [] }), null);
});

test("only fixed Ctrl+Alt scene cycling is accepted when scenes are available", () => {
  const keyboardEvent = {
    altKey: true,
    code: "KeyS",
    ctrlKey: true,
    metaKey: false,
    repeat: false,
    shiftKey: false,
  };
  const lighting = {
    status: "available",
    scenes: ["Bright", "Relax"],
    activeScenes: ["Bright"],
  };

  assert.deepEqual(keyboardAction(keyboardEvent, lighting), {
    action: "room.scene.activate",
    scene: "Relax",
  });
  assert.equal(
    keyboardAction(keyboardEvent, {
      status: "unavailable",
      scenes: [],
      activeScenes: [],
    }),
    null,
  );
  assert.equal(keyboardAction({ ...keyboardEvent, repeat: true }, lighting), null);
  assert.equal(keyboardAction({ ...keyboardEvent, shiftKey: true }, lighting), null);
  assert.equal(keyboardAction({ ...keyboardEvent, metaKey: true }, lighting), null);
});
