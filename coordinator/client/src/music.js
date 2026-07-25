export const initialRoomState = {
  connection: "connecting",
  playback: null,
  interaction: {
    state: "idle",
    message: null,
  },
};

export function roomReducer(state, event) {
  switch (event.type) {
    case "connection":
      return {
        ...state,
        connection: event.state,
      };
    case "playback":
      return {
        ...state,
        playback: event.snapshot,
      };
    case "interaction":
      return {
        ...state,
        interaction: {
          state: event.state,
          message: event.message ?? null,
        },
      };
    default:
      return state;
  }
}

export function projectPosition(playback, now = Date.now()) {
  if (!playback?.item) {
    return 0;
  }

  const duration = playback.item.durationMs;
  let position = playback.positionMs;

  if (playback.status === "playing") {
    const observedAt = Date.parse(playback.observedAt);
    if (Number.isFinite(observedAt)) {
      position += Math.max(0, now - observedAt);
    }
  }

  return Math.min(duration, Math.max(0, Math.round(position)));
}

export function formatTime(milliseconds) {
  const totalSeconds = Math.floor(Math.max(0, milliseconds) / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  if (hours > 0) {
    return `${hours}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
  }

  return `${minutes}:${String(seconds).padStart(2, "0")}`;
}

export function artworkSource(item) {
  if (!item?.artworkUrl) {
    return null;
  }

  try {
    const url = new URL(item.artworkUrl);
    return url.protocol === "https:" ? url.href : null;
  } catch {
    return null;
  }
}
