import assert from "node:assert/strict";
import test from "node:test";
import {
  alarmKeyboardAction,
  alarmTime,
  initialAlarmEditor,
  reduceAlarmEditor,
} from "./alarm-editor.ts";

const disarmed = { status: "disarmed", time: null };
const armed = { status: "armed", time: "07:30" };

test("Alarm editor wraps the selected field and accepts two bounded digits", () => {
  let editor = initialAlarmEditor(disarmed);
  editor = reduceAlarmEditor(editor, { type: "step", amount: 1 });
  assert.equal(alarmTime(editor), "08:00");
  editor = reduceAlarmEditor(editor, { type: "select", selected: "minutes" });
  editor = reduceAlarmEditor(editor, { type: "step", amount: -1 });
  assert.equal(alarmTime(editor), "08:55");
  editor = reduceAlarmEditor(editor, { type: "step", amount: 1, increment: 1 });
  assert.equal(alarmTime(editor), "08:56");
  editor = reduceAlarmEditor(editor, { type: "digit", digit: "4", at: 10 });
  editor = reduceAlarmEditor(editor, { type: "digit", digit: "5", at: 20 });
  assert.equal(alarmTime(editor), "08:45");
  editor = reduceAlarmEditor(editor, { type: "digit", digit: "9", at: 30 });
  assert.equal(
    reduceAlarmEditor(editor, { type: "digit", digit: "9", at: 40 }),
    editor,
  );
});

test("Alarm keyboard scope accepts only its exact editing and action keys", () => {
  const event = {
    altKey: false,
    ctrlKey: false,
    key: "Enter",
    metaKey: false,
    repeat: false,
    shiftKey: false,
  };

  assert.deepEqual(alarmKeyboardAction(event, disarmed), { type: "arm" });
  assert.deepEqual(alarmKeyboardAction({ ...event, key: "Escape" }, armed), {
    type: "disarm",
  });
  assert.deepEqual(alarmKeyboardAction({ ...event, ctrlKey: true }, armed), {
    type: "sleep",
  });
  assert.deepEqual(alarmKeyboardAction({ ...event, key: "ArrowUp" }, disarmed), {
    type: "step",
    amount: 1,
  });
  assert.deepEqual(alarmKeyboardAction({ ...event, key: "ArrowDown" }, disarmed), {
    type: "step",
    amount: -1,
  });
  assert.deepEqual(
    alarmKeyboardAction({ ...event, altKey: true, key: "ArrowUp" }, disarmed),
    { type: "step", amount: 1, increment: 1 },
  );
  assert.deepEqual(
    alarmKeyboardAction({ ...event, altKey: true, key: "ArrowDown" }, disarmed),
    { type: "step", amount: -1, increment: 1 },
  );
  assert.equal(
    alarmKeyboardAction({ ...event, ctrlKey: true, key: "ArrowUp" }, disarmed),
    null,
  );
  assert.equal(alarmKeyboardAction({ ...event, altKey: true }, disarmed), null);
  assert.equal(alarmKeyboardAction(event, armed), null);
  assert.equal(alarmKeyboardAction({ ...event, ctrlKey: true }, disarmed), null);
  assert.equal(alarmKeyboardAction({ ...event, repeat: true }, disarmed), null);
  assert.deepEqual(
    alarmKeyboardAction({ ...event, key: "ArrowUp", repeat: true }, disarmed),
    { type: "step", amount: 1 },
  );
  assert.equal(alarmKeyboardAction({ ...event, key: "a" }, disarmed), null);
});

test("Alarm numeric entry expires and leaves invalid values unchanged", () => {
  let editor = initialAlarmEditor(disarmed);
  editor = reduceAlarmEditor(editor, { type: "digit", digit: "1", at: 10 });
  editor = reduceAlarmEditor(editor, { type: "digit", digit: "2", at: 20 });
  assert.equal(alarmTime(editor), "12:00");
  editor = reduceAlarmEditor(editor, { type: "digit", digit: "2", at: 2000 });
  editor = reduceAlarmEditor(editor, { type: "digit", digit: "8", at: 2010 });
  assert.equal(alarmTime(editor), "12:00");
});
