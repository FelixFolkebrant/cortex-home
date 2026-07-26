import { useLayoutEffect, useRef, useState } from "react";
import { startCameraCapture } from "./camera";
import { cn } from "./classes";

export const cameraStatusCopy = {
  blocked: [
    "Camera blocked by endpoint policy.",
    "This coordinator origin is not permitted to open local video.",
  ],
  denied: [
    "Camera permission denied.",
    "Allow local video for this coordinator origin, then leave and return.",
  ],
  ended: ["Camera stream ended.", "Leave Camera and return to make one fresh attempt."],
  starting: ["Opening the local camera.", "Video stays on this iMac."],
  unavailable: [
    "Camera unavailable.",
    "The front camera is missing, busy, or could not start.",
  ],
  unsupported: [
    "Camera isn’t supported.",
    "This Chromium build cannot open local video.",
  ],
};

export function CameraChannel() {
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

  const copy = cameraStatusCopy[status];

  return (
    <main
      className="absolute inset-0 isolate min-h-screen overflow-hidden bg-[#090807]"
      aria-label="Camera local mirror"
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

      {copy && (
        <div
          className="absolute inset-0 z-10 grid place-content-center bg-[radial-gradient(circle_at_center,rgb(77_61_40_/_32%)_0,transparent_42%),#090807] px-[8vw] text-center"
          role="status"
          aria-live="polite"
        >
          <p className="text-[clamp(0.8rem,1vw,1.1rem)] font-bold tracking-[0.28em] text-[#d6a954] uppercase">
            Cortex Home / Camera
          </p>
          <h1 className="mx-auto mt-7 max-w-[14ch] text-[clamp(3.5rem,7vw,8rem)] leading-[0.92] font-bold tracking-[-0.06em] text-[#fff7e7]">
            {copy[0]}
          </h1>
          <p className="mx-auto mt-7 max-w-[34rem] text-[clamp(1.1rem,1.8vw,1.8rem)] leading-relaxed text-[#c9bda6]">
            {copy[1]}
          </p>
        </div>
      )}

      <div className="absolute right-[clamp(1.5rem,4vw,5rem)] bottom-[clamp(1.5rem,3vw,3rem)] z-20 rounded-2xl border border-white/15 bg-[#090807]/85 px-5 py-4 text-right shadow-2xl backdrop-blur-xl">
        <p className="text-sm font-bold tracking-[0.2em] text-[#fff7e7] uppercase">
          Camera
        </p>
        <p className="mt-1 text-sm text-[#d8ccb6]">
          Local mirror · Video stays on this iMac
        </p>
      </div>
    </main>
  );
}
