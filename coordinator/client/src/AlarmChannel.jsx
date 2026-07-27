import { useEffect, useReducer } from "react";
import {
  alarmKeyboardAction,
  alarmTime,
  initialAlarmEditor,
  reduceAlarmEditor,
} from "./alarm-editor";

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

export function AlarmChannel({ onAction, snapshot }) {
  const [editor, dispatch] = useReducer(
    reduceAlarmEditor,
    snapshot,
    initialAlarmEditor,
  );

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
          </>
        ) : snapshot?.status === "ringing" ? (
          <p>Alarm ringing. Press Enter to dismiss.</p>
        ) : snapshot?.status === "missed" ? (
          <p>This alarm was missed. Set a new wake time.</p>
        ) : snapshot?.status === "failed" ? (
          <p>{snapshot.error || "The alarm could not complete."}</p>
        ) : (
          <>
            <p>Left / Right selects hours or minutes. Up / Down adjusts.</p>
            <p className="mt-3 text-[#f3d18a]">Press Enter to arm.</p>
          </>
        )}
      </div>
    </main>
  );
}
