export const CAMERA_CONSTRAINTS = Object.freeze({
  audio: false,
  video: true,
});

export const CAMERA_LIGHTS = Object.freeze([
  Object.freeze({ color: "transparent", id: "off", label: "Ring light off" }),
  Object.freeze({
    color: "rgb(255 214 158 / 96%)",
    id: "warm",
    label: "Warm light",
  }),
  Object.freeze({
    color: "rgb(255 255 255 / 96%)",
    id: "white",
    label: "White light",
  }),
  Object.freeze({
    color: "rgb(202 232 255 / 96%)",
    id: "cold",
    label: "Cold light",
  }),
]);

export const CAMERA_LIGHT_WIDTHS = Object.freeze([
  Object.freeze({ label: "Narrow", value: "clamp(3rem, 6vw, 7rem)" }),
  Object.freeze({ label: "Medium", value: "clamp(5rem, 10vw, 12rem)" }),
  Object.freeze({ label: "Wide", value: "clamp(7rem, 14vw, 17rem)" }),
  Object.freeze({ label: "Extra wide", value: "clamp(9rem, 18vw, 22rem)" }),
]);

export const DEFAULT_CAMERA_LIGHT_WIDTH = 1;

export function cameraLightAction(event) {
  if (
    event.altKey ||
    event.ctrlKey ||
    event.metaKey ||
    event.shiftKey ||
    event.repeat
  ) {
    return null;
  }

  return (
    {
      ArrowDown: "narrower",
      ArrowLeft: "previous",
      ArrowRight: "next",
      ArrowUp: "wider",
    }[event.code] || null
  );
}

export function cycleCameraLight(current, direction) {
  const step = direction === "previous" ? -1 : 1;
  return (current + step + CAMERA_LIGHTS.length) % CAMERA_LIGHTS.length;
}

export function adjustCameraLightWidth(current, direction) {
  const step = direction === "narrower" ? -1 : 1;
  return Math.max(0, Math.min(CAMERA_LIGHT_WIDTHS.length - 1, current + step));
}

export function cameraFailureStatus(error) {
  switch (error?.name) {
    case "NotAllowedError":
    case "PermissionDeniedError":
      return "denied";
    case "SecurityError":
      return "blocked";
    default:
      return "unavailable";
  }
}

export function stopCameraStream(stream) {
  for (const track of stream?.getTracks?.() || []) {
    track.stop();
  }
}

export function startCameraCapture({
  mediaDevices,
  onStatus,
  pageTarget,
  secureContext,
  video,
}) {
  let active = true;
  let ownedStream = null;
  let ownedTracks = [];

  function publish(status) {
    if (active) {
      onStatus(status);
    }
  }

  function releaseStream() {
    const stream = ownedStream;
    ownedStream = null;

    for (const track of ownedTracks) {
      track.removeEventListener?.("ended", onTrackEnded);
    }
    ownedTracks = [];

    if (video.srcObject === stream) {
      video.srcObject = null;
    }
    stopCameraStream(stream);
  }

  function onTrackEnded() {
    if (!active || !ownedStream) {
      return;
    }

    releaseStream();
    publish("ended");
  }

  function cleanup() {
    if (!active) {
      return;
    }

    active = false;
    pageTarget?.removeEventListener("pagehide", cleanup);
    releaseStream();
  }

  if (secureContext === false) {
    publish("blocked");
    return cleanup;
  }

  if (typeof mediaDevices?.getUserMedia !== "function") {
    publish("unsupported");
    return cleanup;
  }

  pageTarget?.addEventListener("pagehide", cleanup);

  let capture;
  try {
    capture = mediaDevices.getUserMedia(CAMERA_CONSTRAINTS);
  } catch (error) {
    publish(cameraFailureStatus(error));
    return cleanup;
  }

  Promise.resolve(capture).then(
    (stream) => {
      if (!active) {
        stopCameraStream(stream);
        return;
      }

      const tracks = stream?.getTracks?.() || [];
      const videoTracks =
        stream?.getVideoTracks?.() || tracks.filter((track) => track.kind === "video");
      if (videoTracks.length === 0) {
        stopCameraStream(stream);
        publish("unavailable");
        return;
      }

      ownedStream = stream;
      ownedTracks = tracks;
      for (const track of ownedTracks) {
        track.addEventListener?.("ended", onTrackEnded);
      }

      if (videoTracks.some((track) => track.readyState === "ended")) {
        onTrackEnded();
        return;
      }

      try {
        video.srcObject = stream;
      } catch {
        releaseStream();
        publish("unavailable");
        return;
      }
      publish("live");
    },
    (error) => publish(cameraFailureStatus(error)),
  );

  return cleanup;
}
