export const IDENTIFY_ACTION = "endpoint.identify";
export const SCENE_ACTION = "room.scene.activate";
export const CHANNEL_ACTION = "channel.select";
const CHANNELS = ["today", "music", "camera", "airplay", "alarm"];

function adjacentChannel(channel, direction) {
  const currentIndex = Math.max(0, CHANNELS.indexOf(channel));
  const offset = direction === "previous" ? -1 : 1;
  return CHANNELS[(currentIndex + offset + CHANNELS.length) % CHANNELS.length];
}
export const ALARM_ARM_ACTION = "alarm.arm";
export const ALARM_DISARM_ACTION = "alarm.disarm";
export const ALARM_DISMISS_ACTION = "alarm.dismiss";

export const initialRoomState = {
  connection: "connecting",
  channel: null,
  today: null,
  playback: null,
  lighting: null,
  alarm: null,
  interaction: {
    state: "idle",
    action: null,
    level: 0,
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
    case "alarm":
      return {
        ...state,
        alarm: event.snapshot,
      };
    case "interaction":
      return {
        ...state,
        interaction: {
          state: event.state,
          action: event.action ?? null,
          level: event.level ?? 0,
          message: event.message ?? null,
          scene: event.scene ?? null,
        },
      };
    case "interaction.level":
      return {
        ...state,
        interaction: {
          ...state.interaction,
          level: Math.max(0, Math.min(1, event.level)),
        },
      };
    default:
      return state;
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

export function keyboardAction(event, lighting, activeChannel) {
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
    Digit3: "camera",
    Digit4: "airplay",
    Digit5: "alarm",
  }[event.code];
  if (channel) {
    return { action: CHANNEL_ACTION, channel };
  }

  const direction = {
    ArrowLeft: "previous",
    ArrowRight: "next",
  }[event.code];
  if (direction) {
    return {
      action: CHANNEL_ACTION,
      channel: adjacentChannel(activeChannel, direction),
    };
  }

  if (event.code === "KeyS") {
    const scene = nextScene(lighting);
    return scene ? { action: SCENE_ACTION, scene } : null;
  }

  return null;
}
