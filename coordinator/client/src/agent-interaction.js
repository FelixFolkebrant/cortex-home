export const AGENT_INTERACTION_ACTION = "agent.interaction";

function responseError(result, status) {
  return new Error(result?.error || `Coordinator returned ${status}.`);
}

export class SpokenInteraction {
  constructor({
    createAudio = (url) => new Audio(url),
    createObjectURL = (blob) => URL.createObjectURL(blob),
    fetch: request = globalThis.fetch,
    onCompleted,
    onFailed,
    revokeObjectURL = (url) => URL.revokeObjectURL(url),
  }) {
    this.createAudio = createAudio;
    this.createObjectURL = createObjectURL;
    this.fetch = request;
    this.onCompleted = onCompleted;
    this.onFailed = onFailed;
    this.revokeObjectURL = revokeObjectURL;
    this.generation = 0;
    this.session = null;
  }

  owns(requestId) {
    return this.session?.requestId === requestId;
  }

  async start(requestId, capturedAudio, endpointToken) {
    if (this.session) {
      return false;
    }

    const session = {
      audio: null,
      controller: new AbortController(),
      endpointToken,
      generation: ++this.generation,
      requestId,
      url: null,
    };
    this.session = session;

    try {
      const response = await this.fetch(
        `/api/agent/interactions/${encodeURIComponent(requestId)}`,
        {
          body: capturedAudio,
          headers: {
            "Content-Type": "audio/wav",
            "X-Endpoint-Token": endpointToken,
          },
          method: "POST",
          signal: session.controller.signal,
        },
      );
      if (!response.ok) {
        throw responseError(await response.json().catch(() => null), response.status);
      }
      if (response.headers.get("Content-Type") !== "audio/wav") {
        throw new Error("Coordinator returned invalid answer audio.");
      }

      const answerAudio = await response.blob();
      if (!this.isCurrent(session)) {
        return false;
      }
      if (answerAudio.size < 45) {
        throw new Error("Coordinator returned empty answer audio.");
      }

      session.url = this.createObjectURL(answerAudio);
      session.audio = this.createAudio(session.url);
      const playback = this.waitForPlayback(session);
      await session.audio.play();
      if (!this.isCurrent(session)) {
        return false;
      }
      await this.report(session, "speaking");
      await playback;
      if (!this.isCurrent(session)) {
        return false;
      }
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
}
