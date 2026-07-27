import { useEffect, useReducer, useRef, useState } from "react";
import {
  AGENT_INTERACTION_ACTION,
  isVoiceDebugShortcut,
  SpokenInteraction,
} from "./agent-interaction";
import { CameraChannel } from "./CameraChannel";
import { MusicChannel, MusicFullscreen } from "./MusicChannel";
import { RoomFeedback } from "./RoomFeedback";
import {
  CHANNEL_ACTION,
  IDENTIFY_ACTION,
  initialRoomState,
  isMusicFullscreenShortcut,
  keyboardAction,
  roomReducer,
  SCENE_ACTION,
} from "./room-state";
import { TodayChannel } from "./TodayChannel";
import {
  VOICE_CAPTURE_ACTION,
  VoiceCapture,
  voiceCaptureTransition,
} from "./voice-capture";

function writeWavLabel(view, offset, label) {
  for (const [index, character] of [...label].entries()) {
    view.setUint8(offset + index, character.charCodeAt(0));
  }
}

function createIdentifySound() {
  const sampleRate = 44100;
  const channelCount = 2;
  const bytesPerSample = 2;
  const frameSize = channelCount * bytesPerSample;
  const toneDuration = 0.8;
  const toneGap = 0.16;
  const frequencies = [440, 660, 880];
  const signalDuration =
    frequencies.length * toneDuration + (frequencies.length - 1) * toneGap;
  const sampleCount = Math.ceil(signalDuration * sampleRate);
  const dataSize = sampleCount * frameSize;
  const wav = new ArrayBuffer(44 + dataSize);
  const view = new DataView(wav);

  writeWavLabel(view, 0, "RIFF");
  view.setUint32(4, 36 + dataSize, true);
  writeWavLabel(view, 8, "WAVE");
  writeWavLabel(view, 12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, channelCount, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * frameSize, true);
  view.setUint16(32, frameSize, true);
  view.setUint16(34, bytesPerSample * 8, true);
  writeWavLabel(view, 36, "data");
  view.setUint32(40, dataSize, true);

  for (const [toneIndex, frequency] of frequencies.entries()) {
    const toneStart = toneIndex * (toneDuration + toneGap);
    const startSample = Math.floor(toneStart * sampleRate);
    const toneSamples = Math.floor(toneDuration * sampleRate);

    for (let sampleIndex = 0; sampleIndex < toneSamples; sampleIndex += 1) {
      const elapsed = sampleIndex / sampleRate;
      const envelope = Math.sin((Math.PI * sampleIndex) / toneSamples);
      const sample = Math.sin(2 * Math.PI * frequency * elapsed) * envelope * 0.8;
      const frameOffset = 44 + (startSample + sampleIndex) * frameSize;

      for (let channel = 0; channel < channelCount; channel += 1) {
        view.setInt16(frameOffset + channel * bytesPerSample, sample * 32767, true);
      }
    }
  }

  return new Blob([wav], { type: "audio/wav" });
}

async function playIdentifySound() {
  const soundUrl = URL.createObjectURL(createIdentifySound());
  const audio = new Audio(soundUrl);

  try {
    await new Promise((resolve, reject) => {
      audio.addEventListener("ended", resolve, { once: true });
      audio.addEventListener(
        "error",
        () => reject(new Error("Browser audio playback failed.")),
        { once: true },
      );
      audio.play().catch(reject);
    });
  } finally {
    audio.pause();
    URL.revokeObjectURL(soundUrl);
  }
}

export function App() {
  const [room, dispatch] = useReducer(roomReducer, initialRoomState);
  const [musicFullscreen, setMusicFullscreen] = useState(false);
  const [voiceDebug, setVoiceDebug] = useState(null);
  const [voiceDebugVisible, setVoiceDebugVisible] = useState(false);
  const currentClientEntry = document
    .querySelector('script[type="module"][src]')
    ?.getAttribute("src");
  const endpointToken = useRef(null);
  const activeRequestId = useRef(null);
  const lighting = useRef(null);
  const actionGeneration = useRef(0);
  const interactionTimer = useRef(null);
  const activeChannel = useRef("today");
  const voiceRequestId = useRef(null);

  useEffect(() => {
    function clearInteractionTimer() {
      if (interactionTimer.current) {
        window.clearTimeout(interactionTimer.current);
        interactionTimer.current = null;
      }
    }

    function showInteraction(action, state, message, duration, scene) {
      clearInteractionTimer();
      dispatch({ type: "interaction", action, state, message, scene });

      if (duration) {
        interactionTimer.current = window.setTimeout(() => {
          dispatch({ type: "interaction", state: "idle" });
          interactionTimer.current = null;
        }, duration);
      }
    }

    const spokenInteraction = new SpokenInteraction({
      onCompleted: (requestId) => {
        if (voiceRequestId.current !== requestId) {
          return;
        }
        voiceRequestId.current = null;
        activeRequestId.current = null;
        showInteraction(AGENT_INTERACTION_ACTION, "completed", null, 2500);
      },
      onDebug: (requestId, metrics) => {
        if (voiceRequestId.current !== requestId) {
          return;
        }
        setVoiceDebug((current) => ({
          ...(current?.requestId === requestId ? current : {}),
          ...metrics,
          requestId,
        }));
      },
      onFailed: (requestId, error) => {
        if (voiceRequestId.current !== requestId) {
          return;
        }
        voiceRequestId.current = null;
        activeRequestId.current = null;
        showInteraction(AGENT_INTERACTION_ACTION, "failed", error.message, 5000);
      },
    });

    const voiceCapture = new VoiceCapture({
      audioContext: window.AudioContext || window.webkitAudioContext,
      mediaDevices: navigator.mediaDevices,
      onCaptured: (requestId, audio) => {
        if (voiceRequestId.current !== requestId) {
          return;
        }
        if (!endpointToken.current) {
          voiceRequestId.current = null;
          activeRequestId.current = null;
          showInteraction(
            AGENT_INTERACTION_ACTION,
            "failed",
            "The coordinator is unavailable.",
            5000,
          );
          return;
        }
        showInteraction(AGENT_INTERACTION_ACTION, "transcribing");
        void spokenInteraction.start(requestId, audio, endpointToken.current);
      },
      onError: (requestId, error) => {
        if (voiceRequestId.current !== requestId) {
          return;
        }
        voiceRequestId.current = null;
        activeRequestId.current = null;
        setVoiceDebug((current) => ({ ...current, phase: "failed" }));
        showInteraction(VOICE_CAPTURE_ACTION, "failed", error.message, 5000);
      },
      onLevel: (requestId, level) => {
        if (voiceRequestId.current === requestId) {
          dispatch({ type: "interaction.level", level });
        }
      },
      onStarted: (requestId) => {
        if (voiceRequestId.current === requestId) {
          setVoiceDebug((current) => ({ ...current, phase: "capturing" }));
          showInteraction(VOICE_CAPTURE_ACTION, "listening");
        }
      },
    });

    function cancelVoice(message, showFailure = false) {
      const captureCancelled = voiceCapture.cancel(message);
      const interactionCancelled = Boolean(spokenInteraction.session);
      const completion = interactionCancelled
        ? spokenInteraction.cancel()
        : Promise.resolve(false);
      const cancelled = captureCancelled || interactionCancelled;
      if (cancelled) {
        voiceRequestId.current = null;
        activeRequestId.current = null;
      }
      if (interactionCancelled && showFailure) {
        showInteraction(AGENT_INTERACTION_ACTION, "failed", message, 5000);
      }
      return { cancelled, completion };
    }

    async function postStatus(requestId, status, error) {
      const response = await fetch(
        `/api/requests/${encodeURIComponent(requestId)}/status`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Endpoint-Token": endpointToken.current,
          },
          body: JSON.stringify({
            status,
            ...(error ? { error } : {}),
          }),
        },
      );

      if (!response.ok) {
        const result = await response.json().catch(() => ({}));
        throw new Error(result.error || `Coordinator returned ${response.status}.`);
      }
    }

    async function identify(requestId) {
      const generation = ++actionGeneration.current;
      activeRequestId.current = requestId;
      showInteraction(IDENTIFY_ACTION, "identifying");

      try {
        await postStatus(requestId, "identifying");
        await playIdentifySound();

        if (generation !== actionGeneration.current) {
          return;
        }

        await postStatus(requestId, "completed");
        activeRequestId.current = null;
        showInteraction(IDENTIFY_ACTION, "completed", null, 2500);
      } catch (error) {
        if (generation !== actionGeneration.current) {
          return;
        }

        const message = error instanceof Error ? error.message : "Unknown failure.";
        try {
          await postStatus(requestId, "failed", message);
        } catch {
          // The visible failure remains useful when the coordinator is offline.
        }
        activeRequestId.current = null;
        showInteraction(IDENTIFY_ACTION, "failed", message, 5000);
      }
    }

    async function selectChannel(channel) {
      const requestId = `keyboard-${channel}-${Date.now().toString(36)}-${Math.random()
        .toString(36)
        .slice(2, 10)}`;
      activeRequestId.current = requestId;
      showInteraction(CHANNEL_ACTION, "working");

      try {
        const response = await fetch("/api/actions", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ requestId, action: CHANNEL_ACTION, channel }),
        });
        const result = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(result.error || `Coordinator returned ${response.status}.`);
        }
        if (activeRequestId.current === requestId) {
          activeRequestId.current = null;
          showInteraction(CHANNEL_ACTION, "completed", null, 2500);
        }
      } catch (error) {
        if (activeRequestId.current !== requestId) {
          return;
        }
        activeRequestId.current = null;
        const message = error instanceof Error ? error.message : "Unknown failure.";
        showInteraction(CHANNEL_ACTION, "failed", message, 5000);
      }
    }

    async function activateScene(scene) {
      const requestId = `keyboard-scene-${Date.now().toString(36)}-${Math.random()
        .toString(36)
        .slice(2, 10)}`;
      activeRequestId.current = requestId;
      showInteraction(SCENE_ACTION, "working", null, null, scene);

      try {
        const response = await fetch("/api/actions", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            requestId,
            action: SCENE_ACTION,
            scene,
          }),
        });
        const result = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(result.error || `Coordinator returned ${response.status}.`);
        }
        if (activeRequestId.current === requestId) {
          activeRequestId.current = null;
          showInteraction(SCENE_ACTION, "completed", null, 2500, scene);
        }
      } catch (error) {
        if (activeRequestId.current !== requestId) {
          return;
        }
        activeRequestId.current = null;
        const message = error instanceof Error ? error.message : "Unknown failure.";
        showInteraction(SCENE_ACTION, "failed", message, 5000, scene);
      }
    }

    function parseMessage(event) {
      try {
        return JSON.parse(event.data);
      } catch {
        return null;
      }
    }

    const events = new EventSource("/api/events");

    events.addEventListener("ready", (event) => {
      const message = parseMessage(event);
      if (!message) {
        return;
      }

      if (
        currentClientEntry &&
        message.clientEntry &&
        message.clientEntry !== currentClientEntry
      ) {
        events.close();
        window.location.reload();
        return;
      }

      endpointToken.current = message.endpointToken;
      actionGeneration.current += 1;
      const { cancelled } = cancelVoice(
        "Microphone capture was cancelled by reconnection.",
      );
      activeRequestId.current = null;
      dispatch({ type: "connection", state: "connected" });
      if (!cancelled) {
        clearInteractionTimer();
        dispatch({ type: "interaction", state: "idle" });
      }
    });

    events.addEventListener("music.playback", (event) => {
      const snapshot = parseMessage(event);
      if (snapshot) {
        dispatch({ type: "playback", snapshot });
      }
    });

    events.addEventListener("channel.active", (event) => {
      const snapshot = parseMessage(event);
      if (snapshot) {
        activeChannel.current = snapshot.active;
        if (snapshot.active !== "music") {
          setMusicFullscreen(false);
        }
        dispatch({ type: "channel", snapshot });
      }
    });

    events.addEventListener("today.summary", (event) => {
      const snapshot = parseMessage(event);
      if (snapshot) {
        dispatch({ type: "today", snapshot });
      }
    });

    events.addEventListener("room.lighting", (event) => {
      const snapshot = parseMessage(event);
      if (snapshot) {
        lighting.current = snapshot;
        dispatch({ type: "lighting", snapshot });
      }
    });

    events.addEventListener(AGENT_INTERACTION_ACTION, (event) => {
      const message = parseMessage(event);
      if (
        !message ||
        message.requestId !== voiceRequestId.current ||
        !["transcribing", "thinking", "speaking", "completed", "failed"].includes(
          message.phase,
        )
      ) {
        return;
      }

      const terminal = ["completed", "failed"].includes(message.phase);
      if (terminal) {
        spokenInteraction.stop(message.requestId);
        voiceRequestId.current = null;
        activeRequestId.current = null;
      }
      setVoiceDebug((current) =>
        current?.requestId === message.requestId
          ? { ...current, phase: message.phase }
          : current,
      );
      showInteraction(
        AGENT_INTERACTION_ACTION,
        message.phase,
        null,
        terminal ? (message.phase === "completed" ? 2500 : 5000) : null,
      );
    });

    events.addEventListener("action.status", (event) => {
      const message = parseMessage(event);
      if (!message || ![SCENE_ACTION, CHANNEL_ACTION].includes(message.action)) {
        return;
      }

      if (message.status === "accepted") {
        cancelVoice("Microphone capture was cancelled by another room action.");
        activeRequestId.current = message.requestId;
        showInteraction(message.action, "working", null, null, message.scene);
      } else if (
        message.requestId === activeRequestId.current &&
        message.status === "completed"
      ) {
        activeRequestId.current = null;
        showInteraction(message.action, "completed", null, 2500, message.scene);
      } else if (
        message.requestId === activeRequestId.current &&
        message.status === "failed"
      ) {
        activeRequestId.current = null;
        showInteraction(message.action, "failed", message.error, 5000, message.scene);
      }
    });

    events.addEventListener("identify", (event) => {
      const message = parseMessage(event);
      if (message && !activeRequestId.current) {
        identify(message.requestId);
      }
    });

    events.addEventListener("result", (event) => {
      const message = parseMessage(event);
      if (
        message?.requestId === activeRequestId.current &&
        message.status === "failed"
      ) {
        actionGeneration.current += 1;
        activeRequestId.current = null;
        showInteraction(IDENTIFY_ACTION, "failed", message.error, 5000);
      }
    });

    events.onerror = () => {
      endpointToken.current = null;
      actionGeneration.current += 1;
      const { cancelled } = cancelVoice(
        "Microphone capture was cancelled while reconnecting.",
      );
      activeRequestId.current = null;
      dispatch({ type: "connection", state: "disconnected" });
      if (!cancelled) {
        clearInteractionTimer();
        dispatch({ type: "interaction", state: "idle" });
      }
    };

    async function onKeyDown(event) {
      if (isVoiceDebugShortcut(event)) {
        event.preventDefault();
        setVoiceDebugVisible((current) => !current);
        return;
      }

      if (isMusicFullscreenShortcut(event, activeChannel.current)) {
        event.preventDefault();
        setMusicFullscreen((current) => !current);
        return;
      }

      if (voiceCaptureTransition(event) === "start") {
        if (
          activeRequestId.current &&
          !spokenInteraction.owns(activeRequestId.current)
        ) {
          return;
        }
        event.preventDefault();
        const { completion } = cancelVoice(
          "The previous voice interaction was replaced.",
        );
        await completion;
        if (activeRequestId.current) {
          return;
        }
        if (!endpointToken.current) {
          showInteraction(
            AGENT_INTERACTION_ACTION,
            "failed",
            "The coordinator is unavailable.",
            5000,
          );
          return;
        }
        const requestId = `voice-${Date.now().toString(36)}-${Math.random()
          .toString(36)
          .slice(2, 10)}`;
        voiceRequestId.current = requestId;
        activeRequestId.current = requestId;
        setVoiceDebug({ phase: "requesting", requestId });
        showInteraction(VOICE_CAPTURE_ACTION, "requesting");
        voiceCapture.start(requestId);
        return;
      }

      const request = keyboardAction(event, lighting.current);
      if (!request || activeRequestId.current) {
        return;
      }
      event.preventDefault();
      if (request.action === CHANNEL_ACTION) {
        selectChannel(request.channel);
      } else {
        activateScene(request.scene);
      }
    }

    function onKeyUp(event) {
      if (voiceCaptureTransition(event) === "stop" && voiceRequestId.current) {
        event.preventDefault();
        voiceCapture.release(voiceRequestId.current);
      }
    }

    function onBlur() {
      cancelVoice("Voice interaction was cancelled when the display lost focus.", true);
    }

    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("keyup", onKeyUp);
    window.addEventListener("blur", onBlur);

    return () => {
      clearInteractionTimer();
      voiceCapture.dispose();
      spokenInteraction.dispose();
      events.close();
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("keyup", onKeyUp);
      window.removeEventListener("blur", onBlur);
    };
  }, [currentClientEntry]);

  const channel = room.channel?.active || "today";
  const showMusicFullscreen = channel === "music" && musicFullscreen;
  let channelPresentation;
  if (channel === "music") {
    channelPresentation = (
      <MusicChannel playback={room.playback} connection={room.connection} />
    );
  } else if (channel === "camera") {
    channelPresentation = <CameraChannel />;
  } else {
    channelPresentation = <TodayChannel summary={room.today} />;
  }

  return (
    <div className="relative min-h-screen overflow-hidden bg-[#120f0c] text-[#f8f0dc]">
      {showMusicFullscreen ? (
        <MusicFullscreen playback={room.playback} />
      ) : (
        <>
          <div
            aria-hidden="true"
            className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_22%_42%,rgb(111_78_37_/_22%)_0,transparent_34%),radial-gradient(circle_at_78%_68%,rgb(67_51_34_/_18%)_0,transparent_40%),linear-gradient(135deg,#17130f_0%,#0f0d0a_100%)]"
          />
          <div
            aria-hidden="true"
            className="pointer-events-none absolute inset-0 opacity-[0.16] [background-image:linear-gradient(rgb(255_255_255_/_5%)_1px,transparent_1px),linear-gradient(90deg,rgb(255_255_255_/_5%)_1px,transparent_1px)] [background-size:4rem_4rem] [mask-image:linear-gradient(to_bottom,black,transparent_85%)]"
          />

          {channelPresentation}
        </>
      )}

      <RoomFeedback
        connection={room.connection}
        lighting={room.lighting}
        interaction={room.interaction}
        showLightingStatus={channel !== "music"}
        voiceDebug={voiceDebug}
        voiceDebugVisible={voiceDebugVisible}
        voiceOnly={showMusicFullscreen}
      />
    </div>
  );
}
