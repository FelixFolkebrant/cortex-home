export const CAMERA_CONSTRAINTS = Object.freeze({
  audio: false,
  video: true,
});

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
