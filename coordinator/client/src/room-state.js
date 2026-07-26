export const IDENTIFY_ACTION = "endpoint.identify";
export const SCENE_ACTION = "room.scene.activate";
export const CHANNEL_ACTION = "channel.select";

export const initialRoomState = {
  connection: "connecting",
  channel: null,
  today: null,
  playback: null,
  lighting: null,
  interaction: {
    state: "idle",
    action: null,
    message: null,
    scene: null,
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
    case "channel":
      return {
        ...state,
        channel: event.snapshot,
      };
    case "today":
      return {
        ...state,
        today: event.snapshot,
      };
    case "lighting":
      return {
        ...state,
        lighting: event.snapshot,
      };
    case "interaction":
      return {
        ...state,
        interaction: {
          state: event.state,
          action: event.action ?? null,
          message: event.message ?? null,
          scene: event.scene ?? null,
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

export function nextScene(lighting) {
  if (
    lighting?.status !== "available" ||
    !Array.isArray(lighting.scenes) ||
    lighting.scenes.length === 0 ||
    !Array.isArray(lighting.activeScenes)
  ) {
    return null;
  }

  if (lighting.activeScenes.length !== 1) {
    return lighting.scenes[0];
  }

  const activeIndex = lighting.scenes.indexOf(lighting.activeScenes[0]);
  if (activeIndex < 0) {
    return lighting.scenes[0];
  }
  return lighting.scenes[(activeIndex + 1) % lighting.scenes.length];
}

export function keyboardAction(event, lighting) {
  if (
    !event.ctrlKey ||
    !event.altKey ||
    event.metaKey ||
    event.shiftKey ||
    event.repeat
  ) {
    return null;
  }

  const channel = {
    Digit1: "today",
    Digit2: "music",
  }[event.code];
  if (channel) {
    return { action: CHANNEL_ACTION, channel };
  }

  if (event.code === "KeyS") {
    const scene = nextScene(lighting);
    return scene ? { action: SCENE_ACTION, scene } : null;
  }

  return null;
}

export function isMusicFullscreenShortcut(event, channel) {
  return (
    channel === "music" &&
    event.code === "KeyM" &&
    !event.altKey &&
    event.ctrlKey &&
    !event.metaKey &&
    !event.shiftKey &&
    !event.repeat
  );
}
