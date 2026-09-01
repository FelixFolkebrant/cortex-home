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

export class SpokenInteraction {
  constructor({
    createAudio = (url) => new Audio(url),
    createObjectURL = (blob) => URL.createObjectURL(blob),
    fetch: request = (...arguments_) => globalThis.fetch(...arguments_),
    now = () => performance.now(),
    onCompleted,
    onDebug,
    onFailed,
    revokeObjectURL = (url) => URL.revokeObjectURL(url),
  }) {
    this.createAudio = createAudio;
    this.createObjectURL = createObjectURL;
    this.fetch = request;
    this.now = now;
    this.onCompleted = onCompleted;
    this.onDebug = onDebug;
    this.onFailed = onFailed;
    this.revokeObjectURL = revokeObjectURL;
    this.generation = 0;
    this.session = null;
  }

  owns(requestId) {
    return this.session?.requestId === requestId;
  }

  async start(requestId, capturedAudio, endpointToken, sessionId, turnEpoch) {
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
      if (response.headers.get("Content-Type") !== "audio/wav") {
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
    if (!session) {
      return;
    }
    this.session = null;
    this.generation += 1;
    session.controller.abort();
    this.releasePlayback(session);
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
