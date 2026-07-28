const ENTRY_TIMEOUT_MS = 1000;

export const ALARM_ARM_ACTION = "alarm.arm";
export const ALARM_DISARM_ACTION = "alarm.disarm";
export const ALARM_DISMISS_ACTION = "alarm.dismiss";

export function initialAlarmEditor(snapshot) {
  const [hours, minutes] = (snapshot?.time || "07:00").split(":").map(Number);
  return {
    digits: "",
    enteredAt: 0,
    hours,
    minutes,
    selected: "hours",
  };
}

export function alarmTime(editor) {
  return `${String(editor.hours).padStart(2, "0")}:${String(editor.minutes).padStart(2, "0")}`;
}

export function reduceAlarmEditor(editor, action) {
  if (action.type === "select") {
    return { ...editor, digits: "", selected: action.selected };
  }
  if (action.type === "step") {
    const maximum = editor.selected === "hours" ? 23 : 59;
    const increment = action.increment ?? (editor.selected === "hours" ? 1 : 5);
    const value =
      (editor[editor.selected] + action.amount * increment + maximum + 1) %
      (maximum + 1);
    return { ...editor, digits: "", [editor.selected]: value };
  }
  if (action.type === "digit") {
    const digits =
      action.at - editor.enteredAt > ENTRY_TIMEOUT_MS || editor.digits.length === 2
        ? action.digit
        : `${editor.digits}${action.digit}`;
    const maximum = editor.selected === "hours" ? 23 : 59;
    const value = Number(digits);
    if (digits.length === 2 && value > maximum) {
      return editor;
    }
    return {
      ...editor,
      digits,
      enteredAt: action.at,
      ...(digits.length === 2 ? { [editor.selected]: value } : {}),
    };
  }
  if (action.type === "reset") {
    return initialAlarmEditor(action.snapshot);
  }
  return editor;
}

export function alarmKeyboardAction(event, snapshot) {
  if (event.repeat && !["ArrowUp", "ArrowDown"].includes(event.key)) {
    return null;
  }
  if (
    event.key === "Enter" &&
    event.ctrlKey &&
    !event.altKey &&
    !event.metaKey &&
    !event.shiftKey &&
    snapshot?.status === "armed"
  ) {
    return { type: "sleep" };
  }
  if (
    event.metaKey ||
    event.shiftKey ||
    event.ctrlKey ||
    (event.altKey && !["ArrowUp", "ArrowDown"].includes(event.key))
  ) {
    return null;
  }
  if (snapshot?.status === "ringing" && event.key === "Enter") {
    return { type: "dismiss" };
  }
  if (snapshot?.status === "armed" && event.key === "Escape") {
    return { type: "disarm" };
  }
  if (snapshot?.status !== "disarmed") {
    return null;
  }
  if (event.key === "Enter") {
    return { type: "arm" };
  }
  if (event.key === "ArrowLeft") {
    return { type: "select", selected: "hours" };
  }
  if (event.key === "ArrowRight") {
    return { type: "select", selected: "minutes" };
  }
  if (event.key === "ArrowUp") {
    return event.altKey
      ? { type: "step", amount: 1, increment: 1 }
      : { type: "step", amount: 1 };
  }
  if (event.key === "ArrowDown") {
    return event.altKey
      ? { type: "step", amount: -1, increment: 1 }
      : { type: "step", amount: -1 };
  }
  if (/^\d$/.test(event.key)) {
    return { type: "digit", digit: event.key, at: Date.now() };
  }
  return null;
}
