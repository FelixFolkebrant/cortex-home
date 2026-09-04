export const AGENT_INTERACTION_ACTION = "agent.interaction";
const DEBUG_HEADER = "X-Cortex-Debug-Metrics";
const DEBUG_METRICS = new Set([
  "answerBytes",
  "answerCharacters",
  "answerDurationMs",
  "captureBytes",
  "captureDurationMs",
  "llmMs",
  "sttMs",
  "transcriptCharacters",
  "ttsMs",
  "uploadMs",
]);

export function isVoiceDebugShortcut(event) {
  return (
    event.type === "keydown" &&
    event.code === "KeyD" &&
    event.ctrlKey &&
    event.altKey &&
    !event.metaKey &&
    !event.shiftKey &&
    !event.repeat
  );
}

function responseError(result, status) {
  return new Error(result?.error || `Coordinator returned ${status}.`);
}

export function parseDebugMetrics(headers) {
  try {
    const parsed = JSON.parse(headers.get(DEBUG_HEADER));
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      return {};
    }
    return Object.fromEntries(
      Object.entries(parsed).filter(
        ([key, value]) =>
          DEBUG_METRICS.has(key) &&
          typeof value === "number" &&
          Number.isFinite(value) &&
          value >= 0,
      ),
    );
  } catch {
    return {};
  }
}

function captureDuration(capturedAudio) {
  return capturedAudio.size >= 44
    ? Math.round(((capturedAudio.size - 44) / 2 / 16_000) * 1000 * 10) / 10
    : 0;
}

function encodedAudio(encoded) {
  if (typeof encoded !== "string") {
    throw new Error("Coordinator returned invalid streamed audio.");
  }
  const bytes = Uint8Array.from(atob(encoded), (character) => character.charCodeAt(0));
  if (bytes.length < 45) {
    throw new Error("Coordinator returned empty answer audio.");
  }
  return new Blob([bytes], { type: "audio/wav" });
}

export function playbackLevel(samples) {
  if (samples.length === 0) {
    return 0;
  }

  let sum = 0;
  for (const sample of samples) {
    const amplitude = (sample - 128) / 128;
    sum += amplitude * amplitude;
  }
  const rootMeanSquare = Math.sqrt(sum / samples.length);
  return Math.max(0, Math.min(1, (rootMeanSquare - 0.01) * 6));
}

export class SpokenInteraction {
  AudioContext: any;
  cancelFrame: any;
  createAudio: any;
  createObjectURL: any;
  fetch: any;
  now: any;
  onCompleted: any;
  onDebug: any;
  onFailed: any;
  onLevel: any;
  outputContext: any;
  requestFrame: any;
  revokeObjectURL: any;
  generation: number;
  session: any;

  constructor({
    audioContext = globalThis.AudioContext,
    cancelFrame = (frame) => globalThis.cancelAnimationFrame(frame),
    createAudio = (url) => new Audio(url),
    createObjectURL = (blob) => URL.createObjectURL(blob),
    fetch: request = (...arguments_: any[]) => (globalThis.fetch as any)(...arguments_),
    now = () => performance.now(),
    onCompleted,
    onDebug,
    onFailed,
    onLevel,
    requestFrame = (callback) => globalThis.requestAnimationFrame(callback),
    revokeObjectURL = (url) => URL.revokeObjectURL(url),
  }) {
    this.AudioContext = audioContext;
    this.cancelFrame = cancelFrame;
    this.createAudio = createAudio;
    this.createObjectURL = createObjectURL;
    this.fetch = request;
    this.now = now;
    this.onCompleted = onCompleted;
    this.onDebug = onDebug;
    this.onFailed = onFailed;
    this.onLevel = onLevel;
    this.outputContext = null;
    this.requestFrame = requestFrame;
    this.revokeObjectURL = revokeObjectURL;
    this.generation = 0;
    this.session = null;
  }

  owns(requestId) {
    return this.session?.requestId === requestId;
  }

  async start(
    requestId,
    capturedAudio,
    endpointToken,
    sessionId = null,
    turnEpoch = 0,
  ) {
    if (this.session) {
      return false;
    }

    const session = {
      audio: null,
      controller: new AbortController(),
      endpointToken,
      generation: ++this.generation,
      playbackStartedAt: null,
      requestId,
      sessionId,
      startedAt: this.now(),
      playback: Promise.resolve(),
      url: null,
      turnEpoch,
    };
    this.session = session;
    this.debug(session, {
      captureBytes: capturedAudio.size,
      captureDurationMs: captureDuration(capturedAudio),
      phase: "uploading",
    });

    try {
      const response = await this.fetch(
        `/api/agent/interactions/${encodeURIComponent(requestId)}`,
        {
          body: capturedAudio,
          headers: {
            "Content-Type": "audio/wav",
            "X-Endpoint-Token": endpointToken,
            ...(sessionId
              ? {
                  "X-Voice-Session": sessionId,
                  "X-Voice-Turn-Epoch": String(turnEpoch),
                }
              : {}),
          },
          method: "POST",
          signal: session.controller.signal,
        },
      );
      this.debug(session, {
        ...parseDebugMetrics(response.headers),
        phase: response.ok ? "downloading" : "failed",
      });
      if (!response.ok) {
        throw responseError(await response.json().catch(() => null), response.status);
      }
      const contentType = response.headers.get("Content-Type");
      if (sessionId && contentType === "application/json") {
        return true;
      }
      if (contentType !== "audio/wav") {
        throw new Error("Coordinator returned invalid answer audio.");
      }

      const downloadStartedAt = this.now();
      const answerAudio = await response.blob();
      const downloadedAt = this.now();
      if (!this.isCurrent(session)) {
        return false;
      }
      if (answerAudio.size < 45) {
        throw new Error("Coordinator returned empty answer audio.");
      }
      this.debug(session, {
        answerBytes: answerAudio.size,
        answerTransferMs: Math.round((downloadedAt - downloadStartedAt) * 10) / 10,
        phase: "ready",
        totalToAudioMs: Math.round((downloadedAt - session.startedAt) * 10) / 10,
      });

      session.url = this.createObjectURL(answerAudio);
      session.audio = this.createAudio(session.url);
      const playback = this.waitForPlayback(session);
      await this.startLevelMeter(session);
      await session.audio.play();
      if (!this.isCurrent(session)) {
        return false;
      }
      session.playbackStartedAt = this.now();
      this.debug(session, { phase: "speaking" });
      await this.report(session, "speaking");
      await playback;
      if (!this.isCurrent(session)) {
        return false;
      }
      this.debug(session, {
        phase: "completed",
        playbackMs: Math.round((this.now() - session.playbackStartedAt) * 10) / 10,
      });
      await this.report(session, "completed");
      this.finish(session);
      this.onCompleted?.(requestId);
      return true;
    } catch (error) {
      if (!this.isCurrent(session)) {
        return false;
      }
      const message =
        error instanceof Error ? error.message : "Voice interaction failed.";
      this.debug(session, { phase: "failed" });
      try {
        await this.report(session, "failed");
      } catch {
        // The local failure remains visible when the coordinator is offline.
      }
      this.finish(session);
      this.onFailed?.(requestId, new Error(message));
      return false;
    }
  }

  async cancel() {
    const session = this.session;
    if (!session) {
      return false;
    }

    this.debug(session, { phase: "cancelled" });
    this.session = null;
    this.generation += 1;
    session.controller.abort();
    this.releasePlayback(session);
    try {
      await this.fetch(
        `/api/agent/interactions/${encodeURIComponent(session.requestId)}`,
        {
          headers: { "X-Endpoint-Token": session.endpointToken },
          method: "DELETE",
        },
      );
    } catch {
      // Reconnection and server-side endpoint ownership also cancel the request.
    }
    return true;
  }

  stop(requestId) {
    const session = this.session;
    if (!session || session.requestId !== requestId) {
      return false;
    }
    this.session = null;
    this.generation += 1;
    session.controller.abort();
    this.releasePlayback(session);
    return true;
  }

  dispose() {
    const session = this.session;
    if (session) {
      this.session = null;
      this.generation += 1;
      session.controller.abort();
      this.releasePlayback(session);
    }
    this.outputContext?.close().catch(() => {});
    this.outputContext = null;
  }

  async report(session, phase) {
    const response = await this.fetch(
      `/api/agent/interactions/${encodeURIComponent(session.requestId)}/status`,
      {
        body: JSON.stringify({ phase }),
        headers: {
          "Content-Type": "application/json",
          "X-Endpoint-Token": session.endpointToken,
        },
        method: "POST",
        signal: session.controller.signal,
      },
    );
    if (!response.ok) {
      throw responseError(await response.json().catch(() => null), response.status);
    }
  }

  enqueue(requestId, encoded) {
    const session = this.session;
    if (!session || session.requestId !== requestId) {
      return false;
    }
    session.playback = session.playback.then(() => {
      if (!this.isCurrent(session)) {
        return;
      }
      return this.playAudio(
        session,
        encodedAudio(encoded),
        session.playbackStartedAt === null,
      );
    });
    session.playback.catch((error) => this.fail(session, error));
    return true;
  }

  async complete(requestId) {
    const session = this.session;
    if (!session || session.requestId !== requestId) {
      return false;
    }
    try {
      await session.playback;
      if (!this.isCurrent(session)) {
        return false;
      }
      this.debug(session, { phase: "completed" });
      await this.report(session, "completed");
      this.finish(session);
      this.onCompleted?.(requestId);
      return true;
    } catch {
      return false;
    }
  }

  async playAudio(session, answerAudio, reportSpeaking) {
    if (!this.isCurrent(session)) {
      return;
    }
    session.url = this.createObjectURL(answerAudio);
    session.audio = this.createAudio(session.url);
    const playback = this.waitForPlayback(session);
    await this.startLevelMeter(session);
    await session.audio.play();
    if (!this.isCurrent(session)) {
      return;
    }
    if (reportSpeaking) {
      session.playbackStartedAt = this.now();
      this.debug(session, { phase: "speaking" });
      await this.report(session, "speaking");
    }
    await playback;
    this.releasePlayback(session);
  }

  async fail(session, error) {
    if (!this.isCurrent(session)) {
      return;
    }
    const message =
      error instanceof Error ? error.message : "Voice interaction failed.";
    this.debug(session, { phase: "failed" });
    try {
      await this.report(session, "failed");
    } catch {
      // The local failure remains visible when the coordinator is offline.
    }
    this.finish(session);
    this.onFailed?.(session.requestId, new Error(message));
  }

  waitForPlayback(session) {
    return new Promise((resolve, reject) => {
      let settled = false;
      const settle = (result) => {
        if (!settled) {
          settled = true;
          session.settlePlayback = null;
          result();
        }
      };
      session.settlePlayback = () => settle(resolve);
      session.audio.addEventListener("ended", () => settle(resolve), {
        once: true,
      });
      session.audio.addEventListener(
        "error",
        () => settle(() => reject(new Error("Browser audio playback failed."))),
        { once: true },
      );
    });
  }

  finish(session) {
    if (this.isCurrent(session)) {
      this.session = null;
      this.generation += 1;
    }
    this.releasePlayback(session);
  }

  releasePlayback(session) {
    session.settlePlayback?.();
    session.settlePlayback = null;
    this.stopLevelMeter(session);
    if (session.audio) {
      session.audio.pause();
      session.audio.removeAttribute?.("src");
      session.audio.load?.();
      session.audio = null;
    }
    if (session.url) {
      this.revokeObjectURL(session.url);
      session.url = null;
    }
  }

  async startLevelMeter(session) {
    if (!this.AudioContext) {
      return;
    }

    let source = null;
    let analyser = null;
    try {
      this.outputContext ||= new this.AudioContext();
      if (this.outputContext.state === "suspended") {
        await this.outputContext.resume();
      }
      if (!this.isCurrent(session) || this.outputContext.state !== "running") {
        return;
      }

      analyser = this.outputContext.createAnalyser();
      analyser.fftSize = 256;
      source = this.outputContext.createMediaElementSource(session.audio);
      source.connect(this.outputContext.destination);
      source.connect(analyser);
      const meter = {
        analyser,
        frame: null,
        level: 0,
        samples: new Uint8Array(analyser.fftSize),
        source,
      };
      session.meter = meter;
      this.sampleLevel(session, meter);
    } catch {
      source?.disconnect();
      analyser?.disconnect();
    }
  }

  sampleLevel(session, meter) {
    if (!this.isCurrent(session) || session.meter !== meter) {
      return;
    }
    meter.analyser.getByteTimeDomainData(meter.samples);
    const observed = playbackLevel(meter.samples);
    const smoothing = observed > meter.level ? 0.55 : 0.18;
    meter.level += (observed - meter.level) * smoothing;
    if (meter.level < 0.01) {
      meter.level = 0;
    }
    this.onLevel?.(session.requestId, meter.level);
    meter.frame = this.requestFrame(() => this.sampleLevel(session, meter));
  }

  stopLevelMeter(session) {
    const meter = session.meter;
    if (!meter) {
      return;
    }
    session.meter = null;
    if (meter.frame !== null) {
      this.cancelFrame(meter.frame);
    }
    meter.source.disconnect();
    meter.analyser.disconnect();
    this.onLevel?.(session.requestId, 0);
  }

  isCurrent(session) {
    return (
      this.session === session &&
      session.generation === this.generation &&
      !session.controller.signal.aborted
    );
  }

  debug(session, metrics) {
    if (this.isCurrent(session)) {
      this.onDebug?.(session.requestId, metrics);
    }
  }
}
