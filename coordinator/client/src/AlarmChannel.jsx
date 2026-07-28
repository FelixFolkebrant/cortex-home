import { useEffect, useReducer, useState } from "react";
import {
  alarmKeyboardAction,
  alarmTime,
  initialAlarmEditor,
  reduceAlarmEditor,
} from "./alarm-editor";

function stockholmTime(now = new Date()) {
  return new Intl.DateTimeFormat("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    timeZone: "Europe/Stockholm",
  }).format(now);
}

export function AlarmClock() {
  const [now, setNow] = useReducer(() => new Date(), new Date());

  useEffect(() => {
    const timer = window.setInterval(setNow, 1000);
    return () => window.clearInterval(timer);
  }, []);

  return (
    <p className="mt-8 font-mono text-[clamp(6rem,23vw,18rem)] font-semibold leading-none tracking-[-0.09em]">
      {stockholmTime(now)}
    </p>
  );
}

function dateLabel(firesAt) {
  if (!firesAt) {
    return null;
  }
  return new Intl.DateTimeFormat("en-GB", {
    dateStyle: "full",
    timeStyle: "short",
    timeZone: "Europe/Stockholm",
  }).format(new Date(firesAt));
}

export async function requestAlarm(path, fetcher = fetch) {
  const response = await fetcher(`http://127.0.0.1:38019${path}`, {
    method: "POST",
  });
  const result = await response.json().catch(() => ({}));
  if (!response.ok || !["playing", "stopped"].includes(result.state)) {
    throw new Error(result.error || "Alarm audio is unavailable.");
  }
  return result.state;
}

export async function requestSleep(firesAt, fetcher = fetch) {
  const epoch = Math.floor(Date.parse(firesAt) / 1000);
  if (!Number.isSafeInteger(epoch)) {
    throw new Error("The alarm wake time is invalid.");
  }
  const response = await fetcher(`http://127.0.0.1:38019/alarm/sleep/${epoch}`, {
    method: "POST",
  });
  const result = await response.json().catch(() => ({}));
  if (!response.ok || result.state !== "sleeping") {
    throw new Error(result.error || "The iMac could not sleep.");
  }
}

export function AlarmChannel({ onAction, snapshot }) {
  const alarmStatus = snapshot?.status;
  const [editor, dispatch] = useReducer(
    reduceAlarmEditor,
    snapshot,
    initialAlarmEditor,
  );
  const [audioError, setAudioError] = useState(null);

  useEffect(() => {
    if (!alarmStatus) {
      return;
    }
    requestAlarm(alarmStatus === "ringing" ? "/alarm/start" : "/alarm/stop")
      .then(() => setAudioError(null))
      .catch((error) => setAudioError(error.message));
  }, [alarmStatus]);

  useEffect(() => {
    dispatch({ type: "reset", snapshot });
  }, [snapshot]);

  useEffect(() => {
    function onKeyDown(event) {
      const action = alarmKeyboardAction(event, snapshot);
      if (!action) {
        return;
      }
      event.preventDefault();
      if (["select", "step", "digit"].includes(action.type)) {
        dispatch(action);
      } else if (action.type === "arm") {
        onAction("alarm.arm", alarmTime(editor));
      } else if (action.type === "disarm") {
        onAction("alarm.disarm");
      } else if (action.type === "dismiss") {
        onAction("alarm.dismiss");
      } else {
        onAction("alarm.sleep");
      }
    }

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [editor, onAction, snapshot]);

  const editing = snapshot?.status === "disarmed";
  const time = alarmTime(editor);
  const selectedValue = editor.selected === "hours" ? time.slice(0, 2) : time.slice(3);
  const display = editor.digits.length === 1 ? `${editor.digits}_` : selectedValue;

  if (snapshot?.status === "ringing") {
    return (
      <main
        aria-label="Ringing alarm"
        className="relative z-10 grid min-h-screen place-content-center px-8 text-center"
      >
        <p className="text-sm font-semibold uppercase tracking-[0.35em] text-[#f3d18a]">
          Alarm
        </p>
        <AlarmClock />
        <p aria-live="polite" className="mt-12 text-xl text-[#f8f0dc]/75">
          Press Enter to dismiss.
        </p>
        {snapshot.error || audioError ? (
          <p className="mt-4 text-base text-[#ff6961]">
            {snapshot.error || audioError}
          </p>
        ) : null}
      </main>
    );
  }

  return (
    <main
      aria-label="Alarm clock"
      className="relative z-10 grid min-h-screen place-content-center px-8 text-center"
    >
      <p className="text-sm font-semibold uppercase tracking-[0.35em] text-[#f3d18a]">
        Cortex Home / Alarm
      </p>
      <div className="mt-8 flex items-baseline justify-center font-mono text-[clamp(5rem,19vw,15rem)] font-semibold leading-none tracking-[-0.09em]">
        <span
          className={editing && editor.selected === "hours" ? "alarm-selected" : ""}
        >
          {editing && editor.selected === "hours" ? display : time.slice(0, 2)}
        </span>
        <span aria-hidden="true" className="mx-[0.06em] text-[#f3d18a]">
          :
        </span>
        <span
          className={editing && editor.selected === "minutes" ? "alarm-selected" : ""}
        >
          {editing && editor.selected === "minutes" ? display : time.slice(3)}
        </span>
      </div>
      <div aria-live="polite" className="mt-10 min-h-24 text-xl text-[#f8f0dc]/75">
        {snapshot?.status === "armed" ? (
          <>
            <p>Alarm armed for {dateLabel(snapshot.firesAt)}.</p>
            <p className="mt-3 text-[#f3d18a]">Press Ctrl+Enter to sleep.</p>
            <p className="mt-2 text-base">Escape returns to editing.</p>
            {snapshot.error ? (
              <p className="mt-4 text-base text-[#ff6961]">{snapshot.error}</p>
            ) : null}
          </>
        ) : snapshot?.status === "missed" ? (
          <p>This alarm was missed. Set a new wake time.</p>
        ) : snapshot?.status === "failed" ? (
          <p>{snapshot.error || "The alarm could not complete."}</p>
        ) : (
          <>
            <p>Left / Right selects hours or minutes. Up / Down adjusts.</p>
            <p className="mt-2 text-base">
              Minutes change in five-minute steps. Hold Ctrl for one-minute steps.
            </p>
            <p className="mt-3 text-[#f3d18a]">Press Enter to arm.</p>
          </>
        )}
      </div>
    </main>
  );
}
