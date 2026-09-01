export const VOICE_CAPTURE_ACTION = "speech.capture";
export const PCM_SAMPLE_RATE = 16_000;
export const MAX_CAPTURE_SECONDS = 15;
export const MIN_SPEECH_MILLISECONDS = 400;
export const END_OF_TURN_MILLISECONDS = 850;
export const SPEECH_THRESHOLD = 0.018;

const AUTHORITY_KEYS = new Set([
  "AltLeft",
  "AltRight",
  "ControlLeft",
  "ControlRight",
  "Space",
]);

export function voiceCaptureTransition(event) {
  if (
    event.type === "keydown" &&
    event.code === "Space" &&
    event.ctrlKey &&
    event.altKey &&
    !event.metaKey &&
    !event.shiftKey &&
    !event.repeat
  ) {
    return "start";
  }

  if (event.type === "keyup" && AUTHORITY_KEYS.has(event.code)) {
    return "stop";
  }

  return null;
}

export function voiceSessionTransition(event) {
  if (
    event.type === "keydown" &&
    event.code === "Space" &&
    event.ctrlKey &&
    event.altKey &&
    !event.metaKey &&
    !event.shiftKey &&
    !event.repeat
  ) {
    return "toggle";
  }
  if (event.type === "keydown" && event.code === "Escape" && !event.repeat) {
    return "end";
  }
  return null;
}

function writeLabel(view, offset, label) {
  for (const [index, character] of [...label].entries()) {
    view.setUint8(offset + index, character.charCodeAt(0));
  }
}

export function createPcmWav(chunks, sampleRate = PCM_SAMPLE_RATE) {
  const sampleCount = chunks.reduce((total, chunk) => total + chunk.length, 0);
  if (sampleCount === 0) {
    throw new Error("The microphone produced no audio.");
  }
  if (sampleCount > sampleRate * MAX_CAPTURE_SECONDS) {
    throw new Error(`Capture exceeded ${MAX_CAPTURE_SECONDS} seconds.`);
  }

  const bytesPerSample = 2;
  const dataSize = sampleCount * bytesPerSample;
  const wav = new ArrayBuffer(44 + dataSize);
  const view = new DataView(wav);

  writeLabel(view, 0, "RIFF");
  view.setUint32(4, 36 + dataSize, true);
  writeLabel(view, 8, "WAVE");
  writeLabel(view, 12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * bytesPerSample, true);
  view.setUint16(32, bytesPerSample, true);
  view.setUint16(34, bytesPerSample * 8, true);
  writeLabel(view, 36, "data");
  view.setUint32(40, dataSize, true);

  let offset = 44;
  for (const chunk of chunks) {
    for (const sample of chunk) {
      const bounded = Math.max(-1, Math.min(1, sample));
      view.setInt16(offset, bounded < 0 ? bounded * 32768 : bounded * 32767, true);
      offset += bytesPerSample;
    }
  }

  return new Blob([wav], { type: "audio/wav" });
}

export function microphoneLevel(samples) {
  if (samples.length === 0) {
    return 0;
  }

  let sumOfSquares = 0;
  for (const sample of samples) {
    sumOfSquares += sample * sample;
  }
  const rms = Math.sqrt(sumOfSquares / samples.length);
  if (rms === 0) {
    return 0;
  }

  const decibels = 20 * Math.log10(rms);
  return Math.max(0, Math.min(1, (decibels + 60) / 48));
}

export function isSpeech(samples, threshold = SPEECH_THRESHOLD) {
  if (!Number.isFinite(threshold) || threshold <= 0) {
    throw new Error("Speech threshold must be positive.");
  }
  if (!(samples instanceof Float32Array)) {
    throw new Error("Microphone samples must be PCM floats.");
  }
  let sumOfSquares = 0;
  for (const sample of samples) {
    sumOfSquares += sample * sample;
  }
  return samples.length > 0 && Math.sqrt(sumOfSquares / samples.length) >= threshold;
}

function stopTracks(stream) {
  for (const track of stream?.getTracks() || []) {
    track.stop();
  }
}

export class VoiceCapture {
  constructor({
    audioContext,
    audioWorkletNode = globalThis.AudioWorkletNode,
    mediaDevices,
    onCaptured,
    onError,
    onLevel,
    onStarted,
    onTurn,
    onTurnStarted,
    setTimer = (callback, delay) => globalThis.setTimeout(callback, delay),
    clearTimer = (timer) => globalThis.clearTimeout(timer),
    workletUrl = new URL("./pcm-capture-worklet.js", import.meta.url),
  }) {
    this.AudioContext = audioContext;
    this.AudioWorkletNode = audioWorkletNode;
    this.mediaDevices = mediaDevices;
    this.onCaptured = onCaptured;
    this.onError = onError;
    this.onLevel = onLevel;
    this.onStarted = onStarted;
    this.onTurn = onTurn;
    this.onTurnStarted = onTurnStarted;
    this.setTimer = setTimer;
    this.clearTimer = clearTimer;
    this.workletUrl = workletUrl;
    this.generation = 0;
    this.session = null;
  }

  async start(requestId, { continuous = false, turnEpoch = 0 } = {}) {
    if (this.session) {
      return false;
    }

    const generation = ++this.generation;
    const session = {
      chunks: [],
      continuous,
      context: null,
      generation,
      levelReportedAt: null,
      node: null,
      requestId,
      source: null,
      stream: null,
      timer: null,
      turn: null,
      turnEpoch,
      turnDetectionSuspended: false,
    };
    this.session = session;

    if (
      !this.mediaDevices?.getUserMedia ||
      !this.AudioContext ||
      !this.AudioWorkletNode
    ) {
      this.fail(session, new Error("Microphone capture is unavailable."));
      return false;
    }

    try {
      const stream = await this.mediaDevices.getUserMedia({
        audio: {
          autoGainControl: true,
          channelCount: { ideal: 1 },
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: { ideal: PCM_SAMPLE_RATE },
        },
        video: false,
      });
      session.stream = stream;
      if (!this.isCurrent(session)) {
        stopTracks(stream);
        return false;
      }

      const context = new this.AudioContext({ sampleRate: PCM_SAMPLE_RATE });
      session.context = context;
      if (context.sampleRate !== PCM_SAMPLE_RATE) {
        throw new Error("Chromium could not provide 16 kHz microphone audio.");
      }

      await context.audioWorklet.addModule(this.workletUrl);
      if (!this.isCurrent(session)) {
        this.stopSession(session);
        return false;
      }

      session.source = context.createMediaStreamSource(stream);
      session.node = new this.AudioWorkletNode(context, "cortex-pcm-capture");
      const silence = context.createGain();
      silence.gain.value = 0;
      session.node.port.onmessage = ({ data }) => {
        if (this.isCurrent(session) && data instanceof Float32Array) {
          if (!session.continuous) {
            session.chunks.push(data);
          }
          if (session.continuous) {
            this.detectTurn(session, data);
          }
          const now = Date.now();
          if (session.levelReportedAt === null || now - session.levelReportedAt >= 50) {
            session.levelReportedAt = now;
            this.onLevel?.(requestId, microphoneLevel(data));
          }
        }
      };
      session.source.connect(session.node);
      session.node.connect(silence);
      silence.connect(context.destination);
      await context.resume();
      if (!this.isCurrent(session)) {
        this.stopSession(session);
        return false;
      }

      for (const track of stream.getTracks()) {
        track.addEventListener(
          "ended",
          () => {
            if (this.isCurrent(session)) {
              this.fail(session, new Error("The microphone stopped unexpectedly."));
            }
          },
          { once: true },
        );
      }

      if (!session.continuous) {
        session.timer = this.setTimer(() => {
          this.fail(
            session,
            new Error(`Capture exceeded ${MAX_CAPTURE_SECONDS} seconds.`),
          );
        }, MAX_CAPTURE_SECONDS * 1000);
      }
      this.onStarted(requestId);
      return true;
    } catch (error) {
      if (this.isCurrent(session)) {
        this.fail(
          session,
          error instanceof Error ? error : new Error("Microphone capture failed."),
        );
      } else {
        this.stopSession(session);
      }
      return false;
    }
  }

  release(requestId) {
    const session = this.session;
    if (!session || session.requestId !== requestId) {
      return false;
    }

    this.session = null;
    this.generation += 1;
    this.stopSession(session);

    try {
      this.onCaptured(requestId, createPcmWav(session.chunks));
    } catch (error) {
      this.onError(
        requestId,
        error instanceof Error ? error : new Error("Microphone capture failed."),
      );
    }
    return true;
  }

  end(requestId) {
    const session = this.session;
    if (!session || session.requestId !== requestId) {
      return false;
    }
    this.session = null;
    this.generation += 1;
    this.stopSession(session);
    return true;
  }

  suspendTurnDetection() {
    if (!this.session?.continuous) {
      return false;
    }
    this.session.turnDetectionSuspended = true;
    this.session.turn = null;
    return true;
  }

  resumeTurnDetection() {
    if (!this.session?.continuous) {
      return false;
    }
    this.session.turnDetectionSuspended = false;
    return true;
  }

  cancel(message = "Microphone capture was cancelled.") {
    const session = this.session;
    if (!session) {
      return false;
    }

    this.session = null;
    this.generation += 1;
    this.stopSession(session);
    this.onError(session.requestId, new Error(message));
    return true;
  }

  dispose() {
    const session = this.session;
    if (!session) {
      return;
    }

    this.session = null;
    this.generation += 1;
    this.stopSession(session);
  }

  fail(session, error) {
    if (!this.isCurrent(session)) {
      this.stopSession(session);
      return;
    }

    this.session = null;
    this.generation += 1;
    this.stopSession(session);
    this.onError(session.requestId, error);
  }

  isCurrent(session) {
    return this.session === session && session.generation === this.generation;
  }

  stopSession(session) {
    if (session.timer) {
      this.clearTimer(session.timer);
      session.timer = null;
    }
    stopTracks(session.stream);
    session.source?.disconnect();
    session.node?.disconnect();
    session.context?.close().catch(() => {});
  }

  detectTurn(session, samples) {
    if (session.turnDetectionSuspended) {
      return;
    }
    const milliseconds = (samples.length / PCM_SAMPLE_RATE) * 1000;
    const voiced = isSpeech(samples);
    if (!session.turn) {
      if (!voiced) {
        return;
      }
      session.turn = {
        chunks: [samples],
        silenceMs: 0,
        speechMs: milliseconds,
        startedReported: false,
      };
      return;
    }

    session.turn.chunks.push(samples);
    if (voiced) {
      session.turn.speechMs += milliseconds;
      session.turn.silenceMs = 0;
    } else {
      session.turn.silenceMs += milliseconds;
    }
    if (
      !session.turn.startedReported &&
      session.turn.speechMs >= MIN_SPEECH_MILLISECONDS
    ) {
      session.turn.startedReported = true;
      this.onTurnStarted?.(session.requestId, session.turnEpoch + 1);
    }
    const totalSamples = session.turn.chunks.reduce(
      (total, chunk) => total + chunk.length,
      0,
    );
    const reachedEnd =
      session.turn.silenceMs >= END_OF_TURN_MILLISECONDS ||
      totalSamples >= PCM_SAMPLE_RATE * MAX_CAPTURE_SECONDS;
    if (!reachedEnd) {
      return;
    }

    const turn = session.turn;
    session.turn = null;
    if (turn.speechMs < MIN_SPEECH_MILLISECONDS) {
      return;
    }
    session.turnDetectionSuspended = true;
    session.turnEpoch += 1;
    try {
      this.onTurn?.(session.requestId, session.turnEpoch, createPcmWav(turn.chunks));
    } catch (error) {
      this.onError(
        session.requestId,
        error instanceof Error ? error : new Error("Microphone capture failed."),
      );
    }
  }
}
