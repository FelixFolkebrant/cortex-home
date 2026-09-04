import { useLayoutEffect, useRef, useState } from "react";
import { cn } from "../shared/classes";
import { startCameraCapture } from "./camera";

export function CameraMode() {
  const [status, setStatus] = useState("starting");
  const video = useRef(null);

  useLayoutEffect(
    () =>
      startCameraCapture({
        mediaDevices: navigator.mediaDevices,
        onStatus: setStatus,
        pageTarget: window,
        secureContext: window.isSecureContext,
        video: video.current,
      }),
    [],
  );

  return (
    <main
      aria-label="Camera local mirror"
      className="absolute inset-0 min-h-screen overflow-hidden bg-black"
    >
      <video
        aria-label="Mirrored live local camera"
        autoPlay
        className={cn(
          "absolute inset-0 h-full w-full scale-x-[-1] object-cover",
          status !== "live" && "invisible",
        )}
        muted
        playsInline
        ref={video}
      />
    </main>
  );
}
