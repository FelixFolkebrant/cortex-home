import { useEffect, useReducer, useRef, useState } from "react";
import { AlarmRuntime, requestSleep } from "../alarm/AlarmRuntime";
import { CameraMode } from "../camera/CameraMode";
import {
  isSystemStatsDismissShortcut,
  isSystemStatsShortcut,
  SystemStats,
} from "../diagnostics/SystemStats";
import { MusicFullscreen } from "../music/MusicFullscreen";
import { isMusicFullscreenShortcut } from "../music/music-state";
import {
  AGENT_INTERACTION_ACTION,
  isVoiceDebugShortcut,
  SpokenInteraction,
} from "../voice/agent-interaction";
import { RoomFeedback } from "../voice/RoomFeedback";
import {
  VOICE_CAPTURE_ACTION,
  VoiceCapture,
  voiceSessionTransition,
} from "../voice/voice-capture";
import { HomeSurface } from "./HomeSurface";
import {
  DISPLAY_MODE_ACTION,
  IDENTIFY_ACTION,
  initialRoomState,
  isCameraModeShortcut,
  isHomeShortcut,
  keyboardAction,
  roomReducer,
  SCENE_ACTION,
} from "./room-state";

function frontendDiagnostic(event, details = {}) {
  if (import.meta.env.DEV) {
    console.info("cortex-home client:", event, details);
  }
}

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
  const [cameraPhase, setCameraPhase] = useState("home");
  const [musicFullscreen, setMusicFullscreen] = useState(false);
  const [systemStatsVisible, setSystemStatsVisible] = useState(false);
  const [voiceDebug, setVoiceDebug] = useState(null);
  const [voiceDebugVisible, setVoiceDebugVisible] = useState(false);
  const [subtitle, setSubtitle] = useState("");
  const currentClientEntry = document
    .querySelector('script[type="module"][src]')
    ?.getAttribute("src");
  const endpointToken = useRef(null);
  const activeRequestId = useRef(null);
  const lighting = useRef(null);
  const alarmAction = useRef(null);
  const actionGeneration = useRef(0);
  const interactionTimer = useRef(null);
  const cameraPhaseRef = useRef("home");
  const cameraTimer = useRef(null);
  const activeDisplayMode = useRef("home");
  const systemStatsVisibleRef = useRef(false);
  const voiceRequestId = useRef(null);
  const voiceSessionId = useRef(null);
  const subtitleRequestId = useRef(null);

  useEffect(() => {
    let partialTranscriptRequest = null;

    function cancelPartialTranscript() {
      if (partialTranscriptRequest) {
        frontendDiagnostic("partial transcript cancelled");
      }
      partialTranscriptRequest?.abort();
      partialTranscriptRequest = null;
    }

    function clearInteractionTimer() {
      if (interactionTimer.current) {
        window.clearTimeout(interactionTimer.current);
        interactionTimer.current = null;
      }
    }

    function showDisplayMode(mode) {
      if (cameraTimer.current) {
        window.clearTimeout(cameraTimer.current);
        cameraTimer.current = null;
      }
      activeDisplayMode.current = mode;
      if (mode !== "camera") {
        setMusicFullscreen(false);
        cameraPhaseRef.current = "home";
        setCameraPhase("home");
        return;
      }
      if (cameraPhaseRef.current === "camera") {
        return;
      }
      setMusicFullscreen(false);
      systemStatsVisibleRef.current = false;
      setSystemStatsVisible(false);
      cameraPhaseRef.current = "entering";
      setCameraPhase("entering");
      cameraTimer.current = window.setTimeout(() => {
        cameraPhaseRef.current = "camera";
        setCameraPhase("camera");
        cameraTimer.current = null;
      }, 320);
    }

    function showInteraction(
      action,
      state,
      message = null,
      duration = null,
      scene = null,
    ) {
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
        voiceCapture.resumeTurnDetection();
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
        voiceCapture.resumeTurnDetection();
      },
    });

    const voiceCapture = new VoiceCapture({
      audioContext:
        window.AudioContext ||
        (window as typeof window & { webkitAudioContext?: typeof AudioContext })
          .webkitAudioContext,
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
      onTurn: (sessionId, turnEpoch, audio) => {
        if (voiceSessionId.current !== sessionId || voiceRequestId.current) {
          return;
        }
        if (!endpointToken.current) {
          showInteraction(
            AGENT_INTERACTION_ACTION,
            "failed",
            "The coordinator is unavailable.",
            5000,
          );
          voiceCapture.resumeTurnDetection();
          return;
        }
        const requestId = `voice-${sessionId}-${turnEpoch}`;
        voiceRequestId.current = requestId;
        activeRequestId.current = requestId;
        setVoiceDebug({ phase: "uploading", requestId });
        showInteraction(AGENT_INTERACTION_ACTION, "transcribing");
        void spokenInteraction.start(
          requestId,
          audio,
          endpointToken.current,
          sessionId,
          turnEpoch,
        );
      },
      onTurnStarted: (sessionId, turnEpoch) => {
        if (voiceSessionId.current === sessionId && !voiceRequestId.current) {
          subtitleRequestId.current = `voice-${sessionId}-${turnEpoch}`;
          setSubtitle("");
          showInteraction(VOICE_CAPTURE_ACTION, "user-speaking");
        }
      },
      onPartialTurn: (sessionId, turnEpoch, audio) => {
        if (
          voiceSessionId.current !== sessionId ||
          !endpointToken.current ||
          partialTranscriptRequest
        ) {
          return;
        }
        const controller = new AbortController();
        partialTranscriptRequest = controller;
        frontendDiagnostic("partial transcript started", {
          bytes: audio.size,
          turnEpoch,
        });
        void fetch(`/api/voice/sessions/${encodeURIComponent(sessionId)}/transcript`, {
          body: audio,
          headers: {
            "Content-Type": "audio/wav",
            "X-Endpoint-Token": endpointToken.current,
            "X-Voice-Session": sessionId,
            "X-Voice-Turn-Epoch": String(turnEpoch),
          },
          method: "POST",
          signal: controller.signal,
        })
          .then((response) => {
            frontendDiagnostic("partial transcript completed", {
              status: response.status,
              turnEpoch,
            });
          })
          .catch((error) => {
            frontendDiagnostic("partial transcript failed", {
              error: error instanceof Error ? error.name : "UnknownError",
              turnEpoch,
            });
          })
          .finally(() => {
            if (partialTranscriptRequest === controller) {
              partialTranscriptRequest = null;
            }
          });
      },
      onError: (requestId, error) => {
        if (voiceSessionId.current === requestId) {
          subtitleRequestId.current = null;
          setSubtitle("");
          void endVoiceSession(error.message, true);
          return;
        }
        if (voiceRequestId.current !== requestId) {
          return;
        }
        voiceRequestId.current = null;
        activeRequestId.current = null;
        setVoiceDebug((current) => ({ ...current, phase: "failed" }));
        showInteraction(VOICE_CAPTURE_ACTION, "failed", error.message, 5000);
      },
      onLevel: (requestId, level) => {
        if (
          voiceRequestId.current === requestId ||
          voiceSessionId.current === requestId
        ) {
          dispatch({ type: "interaction.level", level });
        }
      },
      onStarted: (requestId) => {
        if (voiceSessionId.current === requestId) {
          setVoiceDebug({ phase: "listening", requestId });
          showInteraction(VOICE_CAPTURE_ACTION, "listening");
        }
      },
    });

    function cancelVoice(message, showFailure = false) {
      cancelPartialTranscript();
      const sessionId = voiceSessionId.current;
      const captureCancelled = sessionId && voiceCapture.end(sessionId);
      const interactionCancelled = Boolean(spokenInteraction.session);
      const completion = interactionCancelled
        ? spokenInteraction.cancel()
        : Promise.resolve(false);
      const cancelled = captureCancelled || interactionCancelled;
      if (cancelled) {
        voiceRequestId.current = null;
        voiceSessionId.current = null;
        activeRequestId.current = null;
        subtitleRequestId.current = null;
        setSubtitle("");
      }
      if (interactionCancelled && showFailure) {
        showInteraction(AGENT_INTERACTION_ACTION, "failed", message, 5000);
      }
      return { cancelled, completion };
    }

    async function endVoiceSession(message, showFailure = false) {
      cancelPartialTranscript();
      const sessionId = voiceSessionId.current;
      if (!sessionId) {
        return false;
      }
      voiceSessionId.current = null;
      voiceCapture.end(sessionId);
      const completion = spokenInteraction.cancel();
      voiceRequestId.current = null;
      activeRequestId.current = null;
      subtitleRequestId.current = null;
      setSubtitle("");
      showInteraction(VOICE_CAPTURE_ACTION, "ending");
      try {
        if (endpointToken.current) {
          await fetch(`/api/voice/sessions/${encodeURIComponent(sessionId)}`, {
            headers: { "X-Endpoint-Token": endpointToken.current },
            method: "DELETE",
          });
        }
      } catch {
        // Reconnection also invalidates the coordinator-owned session.
      }
      await completion;
      if (showFailure) {
        showInteraction(VOICE_CAPTURE_ACTION, "failed", message, 5000);
      } else {
        showInteraction(VOICE_CAPTURE_ACTION, "ended", message, 2500);
      }
      return true;
    }

    async function startVoiceSession() {
      if (!endpointToken.current) {
        showInteraction(
          VOICE_CAPTURE_ACTION,
          "failed",
          "The coordinator is unavailable.",
          5000,
        );
        return;
      }
      const sessionId = `voice-session-${Date.now().toString(36)}-${Math.random()
        .toString(36)
        .slice(2, 10)}`;
      showInteraction(VOICE_CAPTURE_ACTION, "requesting");
      try {
        const response = await fetch(
          `/api/voice/sessions/${encodeURIComponent(sessionId)}`,
          {
            headers: { "X-Endpoint-Token": endpointToken.current },
            method: "POST",
          },
        );
        if (!response.ok) {
          const result = await response.json().catch(() => ({}));
          throw new Error(result.error || "The voice session could not start.");
        }
        const session = await response.json();
        voiceSessionId.current = sessionId;
        if (
          session.sessionId !== sessionId ||
          session.state !== "listening" ||
          !Number.isSafeInteger(session.turnEpoch)
        ) {
          throw new Error("The coordinator returned an invalid voice session.");
        }
        const started = await voiceCapture.start(sessionId, {
          continuous: true,
          turnEpoch: session.turnEpoch,
        });
        if (!started && voiceSessionId.current === sessionId) {
          await endVoiceSession("The microphone request failed.", true);
        }
      } catch (error) {
        if (voiceSessionId.current === sessionId) {
          await endVoiceSession("The voice session could not start.", false);
        }
        const message =
          error instanceof Error ? error.message : "The voice session could not start.";
        showInteraction(VOICE_CAPTURE_ACTION, "failed", message, 5000);
      }
    }

    async function postStatus(requestId, status, error = null) {
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

    async function selectDisplayMode(mode) {
      const requestId = `keyboard-${mode}-${Date.now().toString(36)}-${Math.random()
        .toString(36)
        .slice(2, 10)}`;
      activeRequestId.current = requestId;

      try {
        const response = await fetch("/api/actions", {
          body: JSON.stringify({
            requestId,
            action: DISPLAY_MODE_ACTION,
            mode,
          }),
          headers: { "Content-Type": "application/json" },
          method: "POST",
        });
        const result = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(result.error || `Coordinator returned ${response.status}.`);
        }
        if (activeRequestId.current === requestId) {
          activeRequestId.current = null;
        }
      } catch (error) {
        if (activeRequestId.current !== requestId) {
          return;
        }
        activeRequestId.current = null;
        const message = error instanceof Error ? error.message : "Unknown failure.";
        showInteraction(DISPLAY_MODE_ACTION, "failed", message, 5000);
      }
    }

    async function submitAlarm(action, time) {
      const requestId = `keyboard-alarm-${Date.now().toString(36)}-${Math.random()
        .toString(36)
        .slice(2, 10)}`;
      activeRequestId.current = requestId;
      showInteraction(action, "working");

      try {
        const response = await fetch("/api/actions", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ requestId, action, ...(time ? { time } : {}) }),
        });
        const result = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(result.error || `Coordinator returned ${response.status}.`);
        }
      } catch (error) {
        if (activeRequestId.current !== requestId) {
          return;
        }
        activeRequestId.current = null;
        const message = error instanceof Error ? error.message : "Unknown failure.";
        showInteraction(action, "failed", message, 5000);
      }
    }

    alarmAction.current = submitAlarm;

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
    frontendDiagnostic("event stream created", { readyState: events.readyState });

    events.onopen = () => {
      frontendDiagnostic("event stream opened", { readyState: events.readyState });
    };

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
      frontendDiagnostic("event stream ready", { readyState: events.readyState });
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

    events.addEventListener("display.mode", (event) => {
      const snapshot = parseMessage(event);
      if (snapshot?.active === "home" || snapshot?.active === "camera") {
        showDisplayMode(snapshot.active);
        dispatch({ type: "display.mode", snapshot });
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

    events.addEventListener("alarm.state", (event) => {
      const snapshot = parseMessage(event);
      if (snapshot) {
        dispatch({ type: "alarm", snapshot });
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
        voiceCapture.resumeTurnDetection();
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

    events.addEventListener("agent.transcript", (event) => {
      const message = parseMessage(event);
      if (
        message?.requestId === subtitleRequestId.current &&
        typeof message.text === "string"
      ) {
        setSubtitle(message.text);
      }
    });

    events.addEventListener("agent.audio", (event) => {
      const message = parseMessage(event);
      if (message?.requestId === voiceRequestId.current) {
        spokenInteraction.enqueue(message.requestId, message.audio);
      }
    });

    events.addEventListener("agent.audio.complete", (event) => {
      const message = parseMessage(event);
      if (message?.requestId === voiceRequestId.current) {
        void spokenInteraction.complete(message.requestId);
      }
    });

    events.addEventListener("voice.session", (event) => {
      const session = parseMessage(event);
      if (!session || session.sessionId !== voiceSessionId.current) {
        return;
      }
      if (session.state === "ended") {
        voiceSessionId.current = null;
        voiceRequestId.current = null;
        voiceCapture.end(session.sessionId);
        activeRequestId.current = null;
        subtitleRequestId.current = null;
        setSubtitle("");
        showInteraction(VOICE_CAPTURE_ACTION, "ended", null, 2500);
      }
    });

    events.addEventListener("action.status", (event) => {
      const message = parseMessage(event);
      if (
        !message ||
        ![
          SCENE_ACTION,
          DISPLAY_MODE_ACTION,
          "alarm.arm",
          "alarm.disarm",
          "alarm.dismiss",
          "alarm.sleep",
        ].includes(message.action)
      ) {
        return;
      }

      if (message.status === "accepted") {
        void endVoiceSession("Voice session ended by another room action.");
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

    events.addEventListener("alarm.sleep", (event) => {
      const message = parseMessage(event);
      if (!message?.requestId || !message.firesAt) {
        return;
      }
      requestSleep(message.firesAt)
        .then(() => postStatus(message.requestId, "completed"))
        .catch((error) =>
          postStatus(
            message.requestId,
            "failed",
            error instanceof Error ? error.message : "The iMac could not sleep.",
          ).catch(() => {}),
        );
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
      frontendDiagnostic("event stream error", { readyState: events.readyState });
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
      if (isCameraModeShortcut(event)) {
        if (!activeRequestId.current) {
          event.preventDefault();
          void selectDisplayMode(
            activeDisplayMode.current === "camera" ? "home" : "camera",
          );
        }
        return;
      }

      if (isHomeShortcut(event)) {
        if (!activeRequestId.current) {
          event.preventDefault();
          if (activeDisplayMode.current !== "home") {
            void selectDisplayMode("home");
          }
        }
        return;
      }

      if (cameraPhaseRef.current !== "home") {
        return;
      }

      if (isSystemStatsShortcut(event)) {
        event.preventDefault();
        setSystemStatsVisible((current) => {
          const next = !current;
          systemStatsVisibleRef.current = next;
          return next;
        });
        return;
      }

      if (systemStatsVisibleRef.current && isSystemStatsDismissShortcut(event)) {
        event.preventDefault();
        systemStatsVisibleRef.current = false;
        setSystemStatsVisible(false);
        return;
      }

      if (isVoiceDebugShortcut(event)) {
        event.preventDefault();
        setVoiceDebugVisible((current) => !current);
        return;
      }

      if (isMusicFullscreenShortcut(event)) {
        event.preventDefault();
        setMusicFullscreen((current) => !current);
        return;
      }

      const voiceTransition = voiceSessionTransition(event);
      if (voiceTransition) {
        if (
          activeRequestId.current &&
          !spokenInteraction.owns(activeRequestId.current)
        ) {
          return;
        }
        event.preventDefault();
        if (voiceSessionId.current) {
          await endVoiceSession("Voice session ended.");
        } else if (voiceTransition === "toggle") {
          await startVoiceSession();
        }
        return;
      }

      const request = keyboardAction(event, lighting.current);
      if (!request || activeRequestId.current) {
        return;
      }
      event.preventDefault();
      activateScene(request.scene);
    }

    function onBlur() {
      void endVoiceSession("Voice session ended when the display lost focus.", true);
    }

    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("blur", onBlur);

    return () => {
      clearInteractionTimer();
      cancelPartialTranscript();
      voiceCapture.dispose();
      spokenInteraction.dispose();
      alarmAction.current = null;
      if (cameraTimer.current) {
        window.clearTimeout(cameraTimer.current);
        cameraTimer.current = null;
      }
      frontendDiagnostic("event stream closed by cleanup", {
        readyState: events.readyState,
      });
      events.close();
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("blur", onBlur);
    };
  }, [currentClientEntry]);

  const showMusicFullscreen = cameraPhase === "home" && musicFullscreen;
  const voiceVisualActive =
    [VOICE_CAPTURE_ACTION, AGENT_INTERACTION_ACTION].includes(
      room.interaction.action,
    ) && !["idle", "completed", "ended", "failed"].includes(room.interaction.state);

  return (
    <div className="relative min-h-screen overflow-hidden bg-white text-black">
      <AlarmRuntime
        onDismiss={() => alarmAction.current?.("alarm.dismiss")}
        snapshot={room.alarm}
      />

      {cameraPhase === "camera" ? (
        <CameraMode />
      ) : (
        <div
          className={
            voiceVisualActive
              ? "opacity-[0.12] transition-opacity duration-300 motion-reduce:transition-none"
              : "opacity-100 transition-opacity duration-300 motion-reduce:transition-none"
          }
        >
          {showMusicFullscreen ? (
            <MusicFullscreen playback={room.playback} />
          ) : (
            <HomeSurface
              alarm={room.alarm}
              playback={room.playback}
              summary={room.today}
            />
          )}
        </div>
      )}

      {cameraPhase === "home" ? (
        <RoomFeedback
          connection={room.connection}
          interaction={room.interaction}
          subtitle={subtitle}
          voiceDebug={voiceDebug}
          voiceDebugVisible={voiceDebugVisible}
          voiceOnly={showMusicFullscreen}
        />
      ) : null}

      {cameraPhase === "home" && (
        <SystemStats
          onDismiss={() => {
            systemStatsVisibleRef.current = false;
            setSystemStatsVisible(false);
          }}
          visible={systemStatsVisible}
        />
      )}

      {cameraPhase === "entering" && (
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 z-[100] animate-[camera-blackout_320ms_ease-out_both] bg-black motion-reduce:animate-none motion-reduce:opacity-100"
        />
      )}
    </div>
  );
}
