import assert from "node:assert/strict";
import test from "node:test";
import { contrastingMonochrome, paletteFromPixels } from "./music-palette.js";

function pixels(...entries) {
  const values = [];

  for (const [color, count] of entries) {
    for (let index = 0; index < count; index += 1) {
      values.push(...color, 255);
    }
  }

  return new Uint8ClampedArray(values);
}

test("the most common color becomes the fullscreen background", () => {
  const palette = paletteFromPixels(pixels([[9, 17, 25], 90], [[205, 51, 63], 10]));

  assert.equal(palette.background, "#091119");
  assert.equal(palette.accent, "#cd333f");
  assert.equal(palette.dim, "#ffffff");
});

test("a recurring chromatic detail wins over a common neutral highlight", () => {
  const palette = paletteFromPixels(
    pixels([[8, 12, 20], 80], [[235, 238, 240], 18], [[190, 42, 54], 2]),
  );

  assert.equal(palette.accent, "#be2a36");
});

test("transparent pixels are ignored and an empty image remains unresolved", () => {
  assert.equal(paletteFromPixels(new Uint8ClampedArray([255, 0, 0, 0])), null);
});

test("dim text chooses whichever of black and white contrasts more", () => {
  assert.equal(contrastingMonochrome([245, 245, 245]), "#000000");
  assert.equal(contrastingMonochrome([8, 8, 8]), "#ffffff");
});
