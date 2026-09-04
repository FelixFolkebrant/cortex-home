import { IDENTIFY_ACTION, SCENE_ACTION } from "../app/room-state";
import { AGENT_INTERACTION_ACTION } from "./agent-interaction";
import { VOICE_CAPTURE_ACTION } from "./voice-capture";

function ConnectionNotice({ connection }) {
  if (connection !== "disconnected") {
    return null;
  }

  return (
    <div
      className="absolute top-6 left-1/2 z-30 flex -translate-x-1/2 items-center gap-3 rounded-full border border-black/10 bg-white/90 px-5 py-3 text-sm font-medium tracking-[0.08em] text-black/55 shadow-lg backdrop-blur-xl"
      role="status"
    >
      <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-[#e06745] motion-reduce:animate-none" />
      Coordinator offline
    </div>
  );
}

function InteractionOverlay({ interaction }) {
  if (interaction.state === "idle") {
    return null;
  }

  const scene = interaction.scene || "Scene";
  const copy = {
    [IDENTIFY_ACTION]: {
      completed: ["Identified.", "The room confirmed the request."],
      failed: ["Couldn’t identify.", "The request failed."],
      identifying: ["Here I am.", "Playing the room signal."],
    },
    [SCENE_ACTION]: {
      completed: [`${scene} is active.`, "The room confirmed the scene."],
      failed: ["Couldn’t activate the scene.", "The scene request failed."],
      working: [`Activating ${scene}.`, "Waiting for Hue to confirm the scene."],
    },
  }[interaction.action]?.[interaction.state];
  if (!copy) {
    return null;
  }

  return (
    <div
      className="absolute inset-0 z-40 grid place-content-center bg-white/92 px-[8vw] text-center backdrop-blur-2xl"
      role="status"
      aria-live="assertive"
    >
      <h2 className="mx-auto max-w-[12ch] text-[clamp(4.5rem,9vw,10rem)] leading-[0.88] font-normal tracking-[-0.07em] text-black/70">
        {copy[0]}
      </h2>
      <p className="mt-8 text-[clamp(1.2rem,2vw,2rem)] text-black/45">
        {interaction.message || copy[1]}
      </p>
    </div>
  );
}

function VoiceSun({ interaction }) {
  const listening =
    interaction.action === VOICE_CAPTURE_ACTION &&
    ["requesting", "listening", "user-speaking"].includes(interaction.state);
  const thinking =
    interaction.action === AGENT_INTERACTION_ACTION &&
    ["transcribing", "thinking"].includes(interaction.state);
  const speaking =
    interaction.action === AGENT_INTERACTION_ACTION && interaction.state === "speaking";
  if (!listening && !thinking && !speaking) {
    return null;
  }

  const level = Math.max(0, Math.min(1, interaction.level || 0));
  const label = speaking ? "Agent speaking" : thinking ? "Agent thinking" : "Listening";
  const sun = speaking ? "speaking" : thinking ? "thinking" : "listening";

  return (
    <div
      aria-label={label}
      className="pointer-events-none absolute top-[47%] left-1/2 z-50 -translate-x-1/2 -translate-y-1/2"
      role="status"
    >
      <div
        className="transition-transform duration-75 ease-out motion-reduce:transition-none"
        style={{ transform: `scale(${1 + (listening ? level * 0.1 : 0)})` }}
      >
        <span
          aria-hidden="true"
          className={
            sun === "speaking"
              ? "block size-[clamp(10.5rem,13.3vw,15.4rem)] animate-[voice-speaking_780ms_ease-in-out_infinite_alternate] rounded-full bg-[radial-gradient(circle_at_center,#faf2a3_0%,#fbe27a_25%,#fdd252_50%,#fec129_75%,#ffb100_100%)] shadow-[0_0_3.2rem_1.2rem_#ff9f4b] motion-reduce:animate-none"
              : sun === "thinking"
                ? "block size-[clamp(5.2rem,6.5vw,7.45rem)] animate-[voice-thinking_1.2s_ease-in-out_infinite_alternate] rounded-full bg-[radial-gradient(circle_at_center,#fff0bc_0%,#ffd57c_45%,#ffae2f_100%)] shadow-[0_0_3.2rem_1.2rem_#ffb24b] motion-reduce:animate-none"
                : "block size-[clamp(5.2rem,6.5vw,7.45rem)] animate-[voice-listening_900ms_ease-in-out_infinite_alternate] rounded-full bg-[radial-gradient(circle_at_center,#fab6a3_0%,#fba77a_25%,#fd9952_50%,#fe8a29_75%,#ff7b00_100%)] shadow-[0_0_3.2rem_1.2rem_#ff674b] motion-reduce:animate-none"
          }
        />
      </div>
    </div>
  );
}

export function VoiceSubtitles({ text }) {
  if (!text) {
    return null;
  }

  return (
    <div className="pointer-events-none absolute right-0 bottom-[clamp(6.5rem,13vh,9.5rem)] left-0 z-50 flex justify-center px-6">
      <p className="max-w-[min(90vw,51rem)] bg-black px-4 py-2 text-center text-[clamp(1.45rem,2vw,2.25rem)] leading-[1.35] font-normal text-white">
        {text}
      </p>
    </div>
  );
}

function VoiceInputBar({ interaction }) {
  if (
    interaction.action !== VOICE_CAPTURE_ACTION ||
    !["listening", "user-speaking"].includes(interaction.state)
  ) {
    return null;
  }

  const level = Math.max(0, Math.min(1, interaction.level || 0));

  return (
    <div
      aria-hidden="true"
      className="pointer-events-none absolute right-0 bottom-[clamp(1.7rem,3.8vh,2.7rem)] left-0 z-50 flex justify-center px-6"
    >
      <div className="flex h-6 w-[min(76vw,52rem)] items-center justify-center">
        <span
          className="block h-[clamp(0.65rem,1.1vw,1rem)] min-w-12 rounded-full bg-black transition-[width] duration-75 ease-out motion-reduce:transition-none"
          style={{ width: `${8 + level * 92}%` }}
        />
      </div>
    </div>
  );
}

function formatMilliseconds(value) {
  if (!Number.isFinite(value)) {
    return "—";
  }
  return `${
    value < 100 ? value.toFixed(1) : Math.round(value).toLocaleString("en-US")
  } ms`;
}

function formatAudio(milliseconds, bytes) {
  if (!Number.isFinite(milliseconds) || !Number.isFinite(bytes)) {
    return "—";
  }
  return `${(milliseconds / 1000).toFixed(2)} s · ${(bytes / 1024).toFixed(1)} KiB`;
}

function formatCharacters(value) {
  return Number.isFinite(value) ? `${value} characters` : "—";
}

function VoiceDebugPanel({ debug, visible }) {
  if (!visible) {
    return null;
  }

  const metrics = debug || {};
  const rows = [
    ["Upload transfer", formatMilliseconds(metrics.uploadMs)],
    ["STT", formatMilliseconds(metrics.sttMs)],
    ["LLM round trip", formatMilliseconds(metrics.llmMs)],
    ["TTS", formatMilliseconds(metrics.ttsMs)],
    ["Answer transfer", formatMilliseconds(metrics.answerTransferMs)],
    ["Total to audio", formatMilliseconds(metrics.totalToAudioMs)],
    ["Playback", formatMilliseconds(metrics.playbackMs)],
    ["Capture", formatAudio(metrics.captureDurationMs, metrics.captureBytes)],
    ["Transcript", formatCharacters(metrics.transcriptCharacters)],
    ["Answer", formatAudio(metrics.answerDurationMs, metrics.answerBytes)],
    ["Response", formatCharacters(metrics.answerCharacters)],
  ];

  return (
    <aside
      className="pointer-events-none absolute bottom-[clamp(6.5rem,12vh,10rem)] left-[clamp(1rem,3vw,3rem)] z-[60] w-[min(29rem,calc(100vw-2rem))] rounded-2xl border border-black/15 bg-white/94 p-5 font-mono text-xs text-black/65 shadow-2xl backdrop-blur-xl"
      aria-label="Voice diagnostics"
    >
      <div className="mb-4 flex items-center justify-between gap-4 border-black/10 border-b pb-3">
        <div>
          <p className="font-bold tracking-[0.16em] text-black/75 uppercase">
            Voice diagnostics
          </p>
          <p className="mt-1 text-black/45">Content-free · Ctrl Alt D to hide</p>
        </div>
        <span className="rounded-full bg-black/5 px-3 py-1 text-black/60 uppercase">
          {metrics.phase || "idle"}
        </span>
      </div>
      <dl className="grid grid-cols-[1fr_auto] gap-x-5 gap-y-2">
        {rows.map(([label, value]) => (
          <div className="contents" key={label}>
            <dt>{label}</dt>
            <dd className="text-right text-black/80 tabular-nums">{value}</dd>
          </div>
        ))}
      </dl>
    </aside>
  );
}

export function RoomFeedback({
  connection,
  interaction,
  subtitle,
  voiceDebug,
  voiceDebugVisible = false,
  voiceOnly = false,
}) {
  return (
    <>
      {!voiceOnly && <ConnectionNotice connection={connection} />}
      {!voiceOnly && <InteractionOverlay interaction={interaction} />}
      <VoiceSun interaction={interaction} />
      <VoiceDebugPanel debug={voiceDebug} visible={voiceDebugVisible} />
      <VoiceSubtitles text={subtitle} />
      <VoiceInputBar interaction={interaction} />
    </>
  );
}
