import assert from "node:assert/strict";
import test from "node:test";
import {
  artworkSource,
  formatTime,
  initialRoomState,
  projectPosition,
  roomReducer,
} from "./music.js";

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
