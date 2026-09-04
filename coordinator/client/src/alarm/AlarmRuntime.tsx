import { useEffect } from "react";
import { requestEndpointControl } from "../shared/endpoint-control";

export async function requestAlarm(path, fetcher = fetch) {
  const response = await requestEndpointControl(path, { method: "POST" }, fetcher);
  const result = await response.json().catch(() => ({}));
  if (!response.ok || !["playing", "stopped"].includes(result.state)) {
    throw new Error(result.error || "Alarm audio is unavailable.");
  }
  return result.state;
}

export async function requestSleep(firesAt, fetcher = fetch, wait = undefined) {
  const epoch = Math.floor(Date.parse(firesAt) / 1000);
  if (!Number.isSafeInteger(epoch)) {
    throw new Error("The alarm wake time is invalid.");
  }
  const response = await requestEndpointControl(
    `/alarm/sleep/${epoch}`,
    { method: "POST" },
    fetcher,
    wait,
  );
  const result = await response.json().catch(() => ({}));
  if (!response.ok || result.state !== "sleeping") {
    throw new Error(result.error || "The iMac could not sleep.");
  }
}

export function AlarmRuntime({ onDismiss, snapshot }) {
  const ringing = snapshot?.status === "ringing";

  useEffect(() => {
    requestAlarm(ringing ? "/alarm/start" : "/alarm/stop").catch(() => {});
    return () => {
      if (ringing) {
        void requestAlarm("/alarm/stop");
      }
    };
  }, [ringing]);

  useEffect(() => {
    if (!ringing) {
      return undefined;
    }
    function onKeyDown(event) {
      if (
        event.key === "Enter" &&
        !event.altKey &&
        !event.ctrlKey &&
        !event.metaKey &&
        !event.shiftKey &&
        !event.repeat
      ) {
        event.preventDefault();
        onDismiss();
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onDismiss, ringing]);

  return null;
}
