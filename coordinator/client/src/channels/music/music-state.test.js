import assert from "node:assert/strict";
import test from "node:test";
import {
  artworkSource,
  formatTime,
  isMusicFullscreenShortcut,
  projectPosition,
} from "./music-state.js";

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

test("Ctrl+M toggles the secondary view only from Music", () => {
  const keyboardEvent = {
    altKey: false,
    code: "KeyM",
    ctrlKey: true,
    metaKey: false,
    repeat: false,
    shiftKey: false,
  };

  assert.equal(isMusicFullscreenShortcut(keyboardEvent, "music"), true);
  assert.equal(isMusicFullscreenShortcut(keyboardEvent, "today"), false);
  assert.equal(
    isMusicFullscreenShortcut({ ...keyboardEvent, repeat: true }, "music"),
    false,
  );
  assert.equal(
    isMusicFullscreenShortcut({ ...keyboardEvent, ctrlKey: false }, "music"),
    false,
  );
  assert.equal(
    isMusicFullscreenShortcut({ ...keyboardEvent, altKey: true }, "music"),
    false,
  );
  assert.equal(
    isMusicFullscreenShortcut({ ...keyboardEvent, shiftKey: true }, "music"),
    false,
  );
  assert.equal(
    isMusicFullscreenShortcut({ ...keyboardEvent, metaKey: true }, "music"),
    false,
  );
  assert.equal(
    isMusicFullscreenShortcut({ ...keyboardEvent, code: "F11" }, "music"),
    false,
  );
});
