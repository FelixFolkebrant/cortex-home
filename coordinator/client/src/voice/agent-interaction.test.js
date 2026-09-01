import assert from "node:assert/strict";
import test from "node:test";
import {
  AGENT_INTERACTION_ACTION,
  isVoiceDebugShortcut,
  parseDebugMetrics,
  SpokenInteraction,
} from "./agent-interaction.js";

function response({
  body = new Blob([new Uint8Array(45)], { type: "audio/wav" }),
  contentType = "audio/wav",
  debugMetrics,
  json = {},
  ok = true,
  status = 200,
} = {}) {
  return {
    blob: async () => body,
    headers: {
      get: (name) => {
        if (name === "Content-Type") {
          return contentType;
        }
        if (name === "X-Cortex-Debug-Metrics" && debugMetrics) {
          return JSON.stringify(debugMetrics);
        }
        return null;
      },
    },
    json: async () => json,
    ok,
    status,
  };
}

class FakeAudio {
  constructor() {
    this.listeners = new Map();
    this.paused = 0;
    this.played = 0;
    this.reloaded = 0;
    this.srcRemoved = 0;
  }

  addEventListener(name, listener) {
    this.listeners.set(name, listener);
  }

  emit(name) {
    this.listeners.get(name)?.();
  }

  load() {
    this.reloaded += 1;
  }

  pause() {
    this.paused += 1;
  }

  play() {
    this.played += 1;
    return Promise.resolve();
  }

  removeAttribute(name) {
    assert.equal(name, "src");
    this.srcRemoved += 1;
  }
}

async function until(predicate) {
  for (let index = 0; index < 100; index += 1) {
    if (predicate()) {
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, 0));
  }
  assert.fail("condition was not reached");
}

test("the default fetch keeps the browser global receiver", async () => {
  const originalFetch = globalThis.fetch;
  let receiver;
  globalThis.fetch = function request() {
    receiver = this;
    return Promise.resolve("response");
  };

  try {
    const interaction = new SpokenInteraction({});
    assert.equal(await interaction.fetch("/api/test"), "response");
    assert.equal(receiver, globalThis);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("debug headers accept only finite content-free metrics", () => {
  const metrics = parseDebugMetrics({
    get: () =>
      JSON.stringify({
        answerCharacters: 42,
        llmMs: 123.4,
        privateAnswer: "do not expose",
        sttMs: -1,
        ttsMs: "slow",
      }),
  });

  assert.deepEqual(metrics, {
    answerCharacters: 42,
    llmMs: 123.4,
  });
  assert.deepEqual(parseDebugMetrics({ get: () => "invalid" }), {});
});

test("only exact Ctrl+Alt+D toggles voice diagnostics", () => {
  const event = {
    altKey: true,
    code: "KeyD",
    ctrlKey: true,
    metaKey: false,
    repeat: false,
    shiftKey: false,
    type: "keydown",
  };

  assert.equal(isVoiceDebugShortcut(event), true);
  for (const changed of [
    { code: "KeyE" },
    { altKey: false },
    { ctrlKey: false },
    { metaKey: true },
    { repeat: true },
    { shiftKey: true },
    { type: "keyup" },
  ]) {
    assert.equal(isVoiceDebugShortcut({ ...event, ...changed }), false);
  }
});

test("one captured WAV plays and reports speaking then completion", async () => {
  const requests = [];
  const audio = new FakeAudio();
  const debug = {};
  const times = [0, 10, 20, 30, 40];
  let completed;
  let revoked;
  const interaction = new SpokenInteraction({
    createAudio: (url) => {
      assert.equal(url, "blob:answer");
      return audio;
    },
    createObjectURL: () => "blob:answer",
    fetch: async (url, options) => {
      requests.push({ options, url });
      return response({
        debugMetrics: {
          answerCharacters: 30,
          answerDurationMs: 900,
          captureBytes: 32_044,
          captureDurationMs: 1_000,
          llmMs: 300,
          sttMs: 100,
          transcriptCharacters: 20,
          ttsMs: 200,
          uploadMs: 4,
        },
      });
    },
    now: () => times.shift(),
    onCompleted: (requestId) => {
      completed = requestId;
    },
    onDebug: (_requestId, update) => Object.assign(debug, update),
    onFailed: (_requestId, error) => assert.fail(error),
    revokeObjectURL: (url) => {
      revoked = url;
    },
  });

  const running = interaction.start(
    "voice-1",
    new Blob([new Uint8Array(32_044)], { type: "audio/wav" }),
    "endpoint-token",
  );
  await until(() => requests.length === 2);
  assert.equal(audio.played, 1);
  audio.emit("ended");
  assert.equal(await running, true);

  assert.deepEqual(
    requests.map(({ options, url }) => [
      options.method,
      url,
      options.body instanceof Blob ? "audio" : JSON.parse(options.body).phase,
    ]),
    [
      ["POST", "/api/agent/interactions/voice-1", "audio"],
      ["POST", "/api/agent/interactions/voice-1/status", "speaking"],
      ["POST", "/api/agent/interactions/voice-1/status", "completed"],
    ],
  );
  assert.equal(requests[0].options.headers["X-Endpoint-Token"], "endpoint-token");
  assert.equal(completed, "voice-1");
  assert.equal(revoked, "blob:answer");
  assert.equal(audio.paused, 1);
  assert.equal(interaction.owns("voice-1"), false);
  assert.equal(AGENT_INTERACTION_ACTION, "agent.interaction");
  assert.deepEqual(debug, {
    answerBytes: 45,
    answerCharacters: 30,
    answerDurationMs: 900,
    answerTransferMs: 10,
    captureBytes: 32_044,
    captureDurationMs: 1_000,
    llmMs: 300,
    phase: "completed",
    playbackMs: 10,
    sttMs: 100,
    totalToAudioMs: 20,
    transcriptCharacters: 20,
    ttsMs: 200,
    uploadMs: 4,
  });
});

test("a session plays endpoint audio after its accepted upload", async () => {
  const requests = [];
  const audio = new FakeAudio();
  const encoded = Buffer.from(new Uint8Array(45)).toString("base64");
  const interaction = new SpokenInteraction({
    createAudio: () => audio,
    createObjectURL: () => "blob:stream",
    fetch: async (url, options) => {
      requests.push({ options, url });
      return response({ contentType: "application/json" });
    },
    revokeObjectURL: () => {},
  });

  assert.equal(
    await interaction.start(
      "voice-stream",
      new Blob([new Uint8Array(45)]),
      "endpoint-token",
      "voice-session",
      1,
    ),
    true,
  );
  assert.equal(interaction.enqueue("voice-stream", encoded), true);
  await until(() => audio.played === 1);
  const completed = interaction.complete("voice-stream");
  audio.emit("ended");
  assert.equal(await completed, true);
  assert.deepEqual(
    requests.map(({ options, url }) => [options.method, url]),
    [
      ["POST", "/api/agent/interactions/voice-stream"],
      ["POST", "/api/agent/interactions/voice-stream/status"],
      ["POST", "/api/agent/interactions/voice-stream/status"],
    ],
  );
});

test("cancellation aborts fetch, stops playback, revokes audio, and deletes", async () => {
  const requests = [];
  const audio = new FakeAudio();
  let resolveUpload;
  const interaction = new SpokenInteraction({
    createAudio: () => audio,
    createObjectURL: () => "blob:answer",
    fetch: (url, options) => {
      requests.push({ options, url });
      if (options.method === "DELETE") {
        return Promise.resolve(response({ contentType: "application/json" }));
      }
      return new Promise((resolve) => {
        resolveUpload = resolve;
      });
    },
    revokeObjectURL: () => {},
  });

  const running = interaction.start(
    "voice-cancel",
    new Blob([new Uint8Array(45)]),
    "endpoint-token",
  );
  assert.equal(await interaction.cancel(), true);
  assert.equal(requests[0].options.signal.aborted, true);
  assert.equal(requests[1].options.method, "DELETE");
  resolveUpload(response());
  assert.equal(await running, false);
  assert.equal(interaction.owns("voice-cancel"), false);
});

test("cancellation settles active playback without completing", async () => {
  const requests = [];
  const audio = new FakeAudio();
  let completed = false;
  let revoked;
  const interaction = new SpokenInteraction({
    createAudio: () => audio,
    createObjectURL: () => "blob:answer",
    fetch: async (url, options) => {
      requests.push({ options, url });
      return response({
        contentType: options.method === "POST" ? "audio/wav" : "application/json",
      });
    },
    onCompleted: () => {
      completed = true;
    },
    revokeObjectURL: (url) => {
      revoked = url;
    },
  });

  const running = interaction.start(
    "voice-playing",
    new Blob([new Uint8Array(45)]),
    "endpoint-token",
  );
  await until(() => requests.length === 2);
  assert.equal(await interaction.cancel(), true);

  assert.equal(await running, false);
  assert.equal(requests.at(-1).options.method, "DELETE");
  assert.equal(audio.paused, 1);
  assert.equal(revoked, "blob:answer");
  assert.equal(completed, false);
});

test("cancellation discards every queued session segment", async () => {
  const audios = [];
  const encoded = Buffer.from(new Uint8Array(45)).toString("base64");
  const interaction = new SpokenInteraction({
    createAudio: () => {
      const audio = new FakeAudio();
      audios.push(audio);
      return audio;
    },
    createObjectURL: () => `blob:segment-${audios.length}`,
    fetch: async () => response({ contentType: "application/json" }),
    revokeObjectURL: () => {},
  });

  await interaction.start(
    "voice-queued",
    new Blob([new Uint8Array(45)]),
    "endpoint-token",
    "voice-session",
    1,
  );
  interaction.enqueue("voice-queued", encoded);
  interaction.enqueue("voice-queued", encoded);
  await until(() => audios[0]?.played === 1);

  assert.equal(await interaction.cancel(), true);
  await new Promise((resolve) => setTimeout(resolve, 0));

  assert.equal(audios.length, 1);
  assert.equal(audios[0].played, 1);
});

test("a server failure remains content-free and reports failed once", async () => {
  const requests = [];
  let failure;
  const interaction = new SpokenInteraction({
    fetch: async (url, options) => {
      requests.push({ options, url });
      if (url.endsWith("/status")) {
        return response({ contentType: "application/json" });
      }
      return response({
        contentType: "application/json",
        json: { error: "The voice agent could not answer." },
        ok: false,
        status: 502,
      });
    },
    onFailed: (requestId, error) => {
      failure = { error: error.message, requestId };
    },
  });

  assert.equal(
    await interaction.start("voice-failed", new Blob(["audio"]), "token"),
    false,
  );
  assert.deepEqual(failure, {
    error: "The voice agent could not answer.",
    requestId: "voice-failed",
  });
  assert.equal(JSON.parse(requests[1].options.body).phase, "failed");
});

test("invalid and failed browser audio cannot complete", async () => {
  for (const scenario of ["content-type", "empty", "playback"]) {
    let failed;
    const audio = new FakeAudio();
    if (scenario === "playback") {
      audio.play = () => Promise.reject(new Error("blocked"));
    }
    const interaction = new SpokenInteraction({
      createAudio: () => audio,
      createObjectURL: () => "blob:answer",
      fetch: async (url) => {
        if (url.endsWith("/status")) {
          return response({ contentType: "application/json" });
        }
        if (scenario === "content-type") {
          return response({ contentType: "application/json" });
        }
        if (scenario === "empty") {
          return response({ body: new Blob([]) });
        }
        return response();
      },
      onFailed: (_requestId, error) => {
        failed = error.message;
      },
      revokeObjectURL: () => {},
    });

    await interaction.start(`voice-${scenario}`, new Blob(["audio"]), "token");
    assert.ok(failed);
    assert.equal(interaction.owns(`voice-${scenario}`), false);
  }
});

test("a stale terminal phase stops only its matching local resources", () => {
  const audio = new FakeAudio();
  let revoked = 0;
  const interaction = new SpokenInteraction({
    revokeObjectURL: () => (revoked += 1),
  });
  interaction.session = {
    audio,
    controller: new AbortController(),
    generation: interaction.generation,
    requestId: "voice-current",
    url: "blob:current",
  };

  assert.equal(interaction.stop("voice-stale"), false);
  assert.equal(interaction.stop("voice-current"), true);
  assert.equal(audio.paused, 1);
  assert.equal(revoked, 1);
});
