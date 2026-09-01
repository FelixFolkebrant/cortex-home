import assert from "node:assert/strict";
import test from "node:test";
import {
  createPcmWav,
  END_OF_TURN_MILLISECONDS,
  isSpeech,
  MAX_CAPTURE_SECONDS,
  MIN_SPEECH_MILLISECONDS,
  microphoneLevel,
  PCM_SAMPLE_RATE,
  VoiceCapture,
  voiceCaptureTransition,
  voiceSessionTransition,
} from "./voice-capture.js";

function shortcut(overrides = {}) {
  return {
    altKey: true,
    code: "Space",
    ctrlKey: true,
    metaKey: false,
    repeat: false,
    shiftKey: false,
    type: "keydown",
    ...overrides,
  };
}

test("only the initial exact Ctrl+Alt+Space press starts capture", () => {
  assert.equal(voiceCaptureTransition(shortcut()), "start");
  assert.equal(voiceCaptureTransition(shortcut({ repeat: true })), null);
  assert.equal(voiceCaptureTransition(shortcut({ shiftKey: true })), null);
  assert.equal(voiceCaptureTransition(shortcut({ metaKey: true })), null);
  assert.equal(voiceCaptureTransition(shortcut({ altKey: false })), null);
  assert.equal(voiceCaptureTransition(shortcut({ ctrlKey: false })), null);
  assert.equal(voiceCaptureTransition(shortcut({ code: "Enter" })), null);
});

test("releasing any authority key stops an active chord", () => {
  for (const code of ["Space", "ControlLeft", "ControlRight", "AltLeft", "AltRight"]) {
    assert.equal(voiceCaptureTransition(shortcut({ code, type: "keyup" })), "stop");
  }
  assert.equal(
    voiceCaptureTransition(shortcut({ code: "ShiftLeft", type: "keyup" })),
    null,
  );
});

test("the continuous-session shortcut toggles only on deliberate key presses", () => {
  assert.equal(voiceSessionTransition(shortcut()), "toggle");
  assert.equal(voiceSessionTransition(shortcut({ repeat: true })), null);
  assert.equal(voiceSessionTransition(shortcut({ shiftKey: true })), null);
  assert.equal(
    voiceSessionTransition({ code: "Escape", repeat: false, type: "keydown" }),
    "end",
  );
  assert.equal(
    voiceSessionTransition({ code: "Escape", repeat: true, type: "keydown" }),
    null,
  );
});

test("turn detection requires sustained local speech and a natural pause", async () => {
  const turns = [];
  const capture = new VoiceCapture({
    audioContext: class {},
    audioWorkletNode: class {},
    mediaDevices: {},
    onError: (requestId, error) => assert.fail(`${requestId}: ${error.message}`),
    onTurn: async (sessionId, epoch, audio) => turns.push({ audio, epoch, sessionId }),
  });
  const session = {
    continuous: true,
    requestId: "session-1",
    turn: null,
    turnDetectionSuspended: false,
    turnEpoch: 0,
  };
  const frameCount = Math.ceil((MIN_SPEECH_MILLISECONDS / 1000) * PCM_SAMPLE_RATE);
  const speech = new Float32Array(frameCount).fill(0.08);
  const silence = new Float32Array(
    Math.ceil((END_OF_TURN_MILLISECONDS / 1000) * PCM_SAMPLE_RATE),
  );

  assert.equal(isSpeech(speech), true);
  assert.equal(isSpeech(silence), false);
  capture.detectTurn(session, speech);
  capture.detectTurn(session, silence);

  assert.equal(turns.length, 1);
  assert.equal(turns[0].sessionId, "session-1");
  assert.equal(turns[0].epoch, 1);
  assert.equal(turns[0].audio.type, "audio/wav");
  assert.equal(session.turnDetectionSuspended, true);
});

test("capture output is bounded mono 16 kHz signed 16-bit PCM WAV", async () => {
  const blob = createPcmWav([new Float32Array([-2, -1, -0.5, 0, 0.5, 1, 2])]);
  const view = new DataView(await blob.arrayBuffer());

  assert.equal(blob.type, "audio/wav");
  assert.equal(view.getUint16(20, true), 1);
  assert.equal(view.getUint16(22, true), 1);
  assert.equal(view.getUint32(24, true), PCM_SAMPLE_RATE);
  assert.equal(view.getUint16(34, true), 16);
  assert.equal(view.getUint32(40, true), 14);
  assert.deepEqual(
    Array.from({ length: 7 }, (_, index) => view.getInt16(44 + index * 2, true)),
    [-32768, -32768, -16384, 0, 16383, 32767, 32767],
  );
  assert.equal(MAX_CAPTURE_SECONDS, 15);
});

test("an empty capture fails explicitly", () => {
  assert.throws(() => createPcmWav([]), /produced no audio/);
  assert.throws(
    () => createPcmWav([new Float32Array(PCM_SAMPLE_RATE * MAX_CAPTURE_SECONDS + 1)]),
    /exceeded 15 seconds/,
  );
});

test("microphone level maps room audio onto a bounded visual range", () => {
  assert.equal(microphoneLevel(new Float32Array()), 0);
  assert.equal(microphoneLevel(new Float32Array([0, 0, 0])), 0);
  assert.ok(microphoneLevel(new Float32Array([0.25, -0.25])) > 0.99);
  assert.ok(microphoneLevel(new Float32Array([0.01, -0.01])) > 0);
  assert.ok(microphoneLevel(new Float32Array([0.01, -0.01])) < 1);
});

test("default timers retain the browser global receiver", () => {
  const originalSetTimeout = globalThis.setTimeout;
  const originalClearTimeout = globalThis.clearTimeout;
  let clearedTimer;
  let scheduledDelay;

  globalThis.setTimeout = function (_callback, delay) {
    assert.equal(this, globalThis);
    scheduledDelay = delay;
    return 17;
  };
  globalThis.clearTimeout = function (timer) {
    assert.equal(this, globalThis);
    clearedTimer = timer;
  };

  try {
    const capture = new VoiceCapture({
      audioContext: class {},
      audioWorkletNode: class {},
      mediaDevices: {},
      onCaptured: () => {},
      onError: () => {},
      onStarted: () => {},
    });

    const timer = capture.setTimer(() => {}, 250);
    capture.clearTimer(timer);

    assert.equal(scheduledDelay, 250);
    assert.equal(clearedTimer, 17);
  } finally {
    globalThis.setTimeout = originalSetTimeout;
    globalThis.clearTimeout = originalClearTimeout;
  }
});

test("a completed session resumes audio, returns PCM, and stops its track", async () => {
  let stopped = 0;
  let resumed = 0;
  const source = {
    connect: () => {},
    disconnect: () => {},
  };
  const stream = {
    getTracks: () => [
      {
        addEventListener: () => {},
        stop: () => (stopped += 1),
      },
    ],
  };
  class FakeContext {
    constructor() {
      this.audioWorklet = { addModule: async () => {} };
      this.destination = {};
      this.sampleRate = PCM_SAMPLE_RATE;
    }

    close() {
      return Promise.resolve();
    }

    createGain() {
      return {
        connect: () => {},
        gain: { value: 1 },
      };
    }

    createMediaStreamSource() {
      return source;
    }

    async resume() {
      resumed += 1;
    }
  }
  class FakeWorkletNode {
    constructor() {
      this.port = {};
    }

    connect() {}

    disconnect() {}
  }
  let result;
  let level;
  const capture = new VoiceCapture({
    audioContext: FakeContext,
    audioWorkletNode: FakeWorkletNode,
    clearTimer: () => {},
    mediaDevices: { getUserMedia: async () => stream },
    onCaptured: (requestId, audio) => {
      result = { audio, requestId };
    },
    onError: (_requestId, error) => assert.fail(error),
    onLevel: (_requestId, currentLevel) => {
      level = currentLevel;
    },
    onStarted: () => {},
    setTimer: () => 1,
  });

  await capture.start("voice-complete");
  capture.session.node.port.onmessage({
    data: new Float32Array([0, 0.5, -0.5]),
  });
  capture.release("voice-complete");

  assert.equal(resumed, 1);
  assert.equal(stopped, 1);
  assert.equal(result.requestId, "voice-complete");
  assert.equal(result.audio.type, "audio/wav");
  assert.ok(level > 0);
});

test("release before permission resolution stops the stale stream", async () => {
  let resolveStream;
  const streamPromise = new Promise((resolve) => {
    resolveStream = resolve;
  });
  let stopped = 0;
  const stream = {
    getTracks: () => [{ stop: () => (stopped += 1) }],
  };
  const errors = [];
  const capture = new VoiceCapture({
    audioContext: class {},
    audioWorkletNode: class {},
    mediaDevices: { getUserMedia: () => streamPromise },
    onCaptured: () => assert.fail("stale audio must not be captured"),
    onError: (_requestId, error) => errors.push(error.message),
    onStarted: () => assert.fail("stale capture must not start"),
  });

  const starting = capture.start("voice-1");
  capture.release("voice-1");
  resolveStream(stream);
  await starting;

  assert.equal(stopped, 1);
  assert.deepEqual(errors, ["The microphone produced no audio."]);
});

test("cancellation immediately stops every owned track", () => {
  let stopped = 0;
  const capture = new VoiceCapture({
    audioContext: class {},
    audioWorkletNode: class {},
    mediaDevices: {},
    onCaptured: () => {},
    onError: () => {},
    onStarted: () => {},
  });
  capture.session = {
    context: null,
    node: null,
    requestId: "voice-2",
    source: null,
    stream: {
      getTracks: () => [{ stop: () => (stopped += 1) }, { stop: () => (stopped += 1) }],
    },
    timer: null,
  };

  capture.cancel();

  assert.equal(stopped, 2);
  assert.equal(capture.session, null);
});
