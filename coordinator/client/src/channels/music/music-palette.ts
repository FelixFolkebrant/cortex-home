export const FALLBACK_MUSIC_PALETTE = {
  accent: "#f8f0dc",
  background: "#080808",
  dim: "#ffffff",
};

function colorKey(red, green, blue) {
  return `${red >> 5}-${green >> 5}-${blue >> 5}`;
}

function channelLuminance(channel) {
  const value = channel / 255;
  return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
}

function luminance([red, green, blue]) {
  return (
    0.2126 * channelLuminance(red) +
    0.7152 * channelLuminance(green) +
    0.0722 * channelLuminance(blue)
  );
}

function contrastRatio(first, second) {
  const lighter = Math.max(luminance(first), luminance(second));
  const darker = Math.min(luminance(first), luminance(second));
  return (lighter + 0.05) / (darker + 0.05);
}

export function contrastingMonochrome(color) {
  return contrastRatio(color, [0, 0, 0]) >= contrastRatio(color, [255, 255, 255])
    ? "#000000"
    : "#ffffff";
}

function colorDistance(first, second) {
  return Math.hypot(first[0] - second[0], first[1] - second[1], first[2] - second[2]);
}

function saturation([red, green, blue]) {
  const maximum = Math.max(red, green, blue);
  const minimum = Math.min(red, green, blue);
  return maximum === 0 ? 0 : (maximum - minimum) / maximum;
}

function averageColor(cluster) {
  return cluster.totals.map((total) => Math.round(total / cluster.count));
}

function colorHex(color) {
  return `#${color.map((channel) => channel.toString(16).padStart(2, "0")).join("")}`;
}

export function paletteFromPixels(pixels) {
  const clusters = new Map();
  let sampleCount = 0;

  for (let index = 0; index < pixels.length; index += 4) {
    if (pixels[index + 3] < 128) {
      continue;
    }

    const color = [pixels[index], pixels[index + 1], pixels[index + 2]];
    const key = colorKey(color[0], color[1], color[2]);
    const cluster = clusters.get(key) || {
      count: 0,
      totals: [0, 0, 0],
    };

    cluster.count += 1;
    cluster.totals = cluster.totals.map((total, channel) => total + color[channel]);
    clusters.set(key, cluster);
    sampleCount += 1;
  }

  if (sampleCount === 0) {
    return null;
  }

  const ranked = [...clusters.values()].sort(
    (first, second) => second.count - first.count,
  );
  const background = averageColor(ranked[0]);
  const minimumPresence = Math.max(2, Math.ceil(sampleCount * 0.003));
  const candidates = ranked
    .slice(1)
    .filter((cluster) => cluster.count >= minimumPresence);

  let accent = null;
  let accentScore = 0;

  for (const cluster of candidates) {
    const color = averageColor(cluster);
    const distance = colorDistance(color, background) / 441.67;
    const presence = Math.min(1, cluster.count / (sampleCount * 0.04));
    const score =
      distance *
      (0.18 + saturation(color) * 0.82) *
      (0.35 + Math.sqrt(presence) * 0.65);

    if (score > accentScore) {
      accent = color;
      accentScore = score;
    }
  }

  const dim = contrastingMonochrome(background);

  return {
    accent: accent ? colorHex(accent) : dim,
    background: colorHex(background),
    dim,
  };
}

export function paletteFromImage(image) {
  const canvas = document.createElement("canvas");
  const context = canvas.getContext("2d", { willReadFrequently: true });

  if (!context) {
    return null;
  }

  canvas.width = 64;
  canvas.height = 64;

  try {
    context.drawImage(image, 0, 0, canvas.width, canvas.height);
    return paletteFromPixels(
      context.getImageData(0, 0, canvas.width, canvas.height).data,
    );
  } catch {
    return null;
  }
}
