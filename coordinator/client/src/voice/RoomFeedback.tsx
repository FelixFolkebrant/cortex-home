import { cva } from "class-variance-authority";
import { CHANNEL_ACTION, IDENTIFY_ACTION, SCENE_ACTION } from "../app/room-state";
import { cn } from "../shared/classes";
import { AGENT_INTERACTION_ACTION } from "./agent-interaction";
import { VOICE_CAPTURE_ACTION } from "./voice-capture";

const interactionCopy = {
  [IDENTIFY_ACTION]: {
    identifying: ["Here I am.", "Playing the room signal."],
    completed: ["Identified.", "The room confirmed the request."],
    failed: ["Couldn’t identify.", "The request failed."],
  },
  [CHANNEL_ACTION]: {
    working: ["Changing view.", "Showing the selected room view."],
    completed: ["View ready.", "The room updated its active view."],
    failed: ["Couldn’t change view.", "The channel request failed."],
  },
  [VOICE_CAPTURE_ACTION]: {
    requesting: ["Opening microphone.", "Waiting for the room microphone."],
    listening: ["Listening.", "Speak naturally. Press Control, Alt, and Space to end."],
    "user-speaking": ["Hearing you.", "Pause naturally when you are finished."],
    ending: ["Ending voice session.", "Closing the microphone and current turn."],
    ended: ["Voice session ended.", "The microphone is no longer active."],
    failed: ["Couldn’t capture.", "The microphone request failed."],
  },
  [AGENT_INTERACTION_ACTION]: {
    transcribing: ["Transcribing.", "Turning the bounded utterance into text."],
    thinking: ["Thinking.", "Using the current room context."],
    speaking: ["Speaking.", "Playing one short answer."],
    completed: ["Answered.", "The contextual answer completed."],
    failed: ["Couldn’t answer.", "The voice interaction failed."],
  },
};

const signal = cva(
  "mx-auto mt-12 aspect-square w-[clamp(7rem,12vw,12rem)] rounded-full border-2 transition-[border-color,box-shadow,transform] duration-300 motion-reduce:animate-none motion-reduce:transition-none",
  {
    variants: {
      state: {
        identifying:
          "animate-identify border-[#ffd27d] shadow-[0_0_0_2rem_rgb(255_210_125_/_16%),0_0_9rem_rgb(255_177_63_/_70%)]",
        working:
          "animate-identify border-[#ffd27d] shadow-[0_0_0_2rem_rgb(255_210_125_/_16%),0_0_9rem_rgb(255_177_63_/_70%)]",
        completed:
          "scale-[1.08] border-[#92d6a1] shadow-[0_0_0_1.5rem_rgb(146_214_161_/_14%),0_0_7rem_rgb(146_214_161_/_45%)]",
        failed:
          "border-[#e67d6f] shadow-[0_0_0_1.5rem_rgb(230_125_111_/_12%),0_0_6rem_rgb(230_125_111_/_38%)]",
      },
    },
  },
);

function ConnectionNotice({ connection }) {
  if (connection !== "disconnected") {
    return null;
  }

  return (
    <div
      className="absolute top-[clamp(1.5rem,3vw,3rem)] right-[clamp(1.5rem,4vw,5rem)] z-30 flex items-center gap-3 rounded-full border border-[#e9bd68]/30 bg-[#17130f]/90 px-5 py-3 text-sm font-bold tracking-[0.12em] text-[#f0d79d] uppercase shadow-2xl backdrop-blur-xl max-sm:top-[5.5rem]"
      role="status"
    >
      <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-[#e9bd68] motion-reduce:animate-none" />
      Coordinator offline · Reconnecting
    </div>
  );
}

function LightingStatus({ lighting }) {
  const status = lighting?.status || "unavailable";
  const activeScenes = lighting?.activeScenes || [];
  let label = "Scenes unavailable";
  let indicator = "bg-[#b87568]";
  if (status === "available" && activeScenes.length === 0) {
    label = "Custom lighting";
    indicator = "bg-[#736959]";
  } else if (status === "available") {
    label = `${activeScenes.join(" + ")} active`;
    indicator = "bg-[#efc66f] shadow-[0_0_1rem_rgb(239_198_111_/_75%)]";
  }

  return (
    <div
      className="absolute top-[clamp(1.5rem,3vw,3rem)] left-[clamp(1.5rem,4vw,5rem)] z-30 flex items-center gap-3 rounded-full border border-white/10 bg-[#17130f]/85 px-5 py-3 text-sm font-bold tracking-[0.12em] text-[#d8ccb6] uppercase shadow-2xl backdrop-blur-xl"
      role="status"
      aria-live="polite"
    >
      <span className={cn("h-2.5 w-2.5 rounded-full", indicator)} />
      {label}
    </div>
  );
}

function InteractionOverlay({ interaction }) {
  if (
    interaction.state === "idle" ||
    interaction.action === CHANNEL_ACTION ||
    interaction.action === VOICE_CAPTURE_ACTION ||
    interaction.action === AGENT_INTERACTION_ACTION
  ) {
    return null;
  }

  const scene = interaction.scene || "Scene";
  const sceneCopy = {
    working: [`Activating ${scene}.`, "Waiting for Hue to confirm the scene."],
    completed: [`${scene} is active.`, "The room confirmed the scene."],
    failed: [`Couldn’t activate ${scene}.`, "The scene request failed."],
  };
  const copy =
    interaction.action === SCENE_ACTION
      ? sceneCopy[interaction.state]
      : interactionCopy[interaction.action]?.[interaction.state];
  if (!copy) {
    return null;
  }
  const [title, defaultMessage] = copy;
  const label = {
    [CHANNEL_ACTION]: "Cortex Home / Channel",
    [IDENTIFY_ACTION]: "Cortex Home / Room signal",
    [SCENE_ACTION]: "Cortex Home / Lighting",
    [VOICE_CAPTURE_ACTION]: "Cortex Home / Microphone",
  }[interaction.action];

  return (
    <div
      className="absolute inset-0 z-40 grid place-content-center bg-[#120f0c]/88 px-[8vw] text-center backdrop-blur-2xl"
      role="status"
      aria-live="assertive"
    >
      <p className="mb-7 text-[clamp(0.85rem,1vw,1.1rem)] font-bold tracking-[0.28em] text-[#d6a954] uppercase">
        {label}
      </p>
      <h2 className="mx-auto max-w-[12ch] text-[clamp(4.5rem,9vw,10rem)] leading-[0.88] font-bold tracking-[-0.07em] text-[#fff7e7]">
        {title}
      </h2>
      <p className="mt-8 text-[clamp(1.2rem,2vw,2rem)] text-[#c9bda6]">
        {interaction.message || defaultMessage}
      </p>
      <div aria-hidden="true" className={signal({ state: interaction.state })} />
    </div>
  );
}

function VoiceCaptureBar({ interaction }) {
  if (
    ![AGENT_INTERACTION_ACTION, VOICE_CAPTURE_ACTION].includes(interaction.action) ||
    interaction.state === "idle"
  ) {
    return null;
  }

  const copy = interactionCopy[interaction.action][interaction.state];
  if (!copy) {
    return null;
  }
  const [title, defaultMessage] = copy;
  const level = Math.max(0, Math.min(1, interaction.level || 0));
  const width = {
    completed: 100,
    ending: 100,
    ended: 100,
    failed: 100,
    listening: 10 + level * 90,
    requesting: 18,
    speaking: 90,
    thinking: 66,
    transcribing: 40,
    "user-speaking": 10 + level * 90,
  }[interaction.state];
  const tone = {
    completed: "bg-[#92d6a1] shadow-[0_0_1.5rem_rgb(146_214_161_/_55%)]",
    ending: "animate-pulse bg-[#736959] motion-reduce:animate-none",
    ended: "bg-[#736959]",
    failed: "bg-[#e67d6f] shadow-[0_0_1.5rem_rgb(230_125_111_/_55%)]",
    listening: "bg-[#d6a954] shadow-[0_0_1.75rem_rgb(214_169_84_/_65%)]",
    requesting:
      "animate-pulse bg-[#d6a954] shadow-[0_0_1.5rem_rgb(214_169_84_/_55%)] motion-reduce:animate-none",
    speaking:
      "animate-pulse bg-[#92d6a1] shadow-[0_0_1.75rem_rgb(146_214_161_/_60%)] motion-reduce:animate-none",
    thinking:
      "animate-pulse bg-[#d6a954] shadow-[0_0_1.5rem_rgb(214_169_84_/_55%)] motion-reduce:animate-none",
    transcribing:
      "animate-pulse bg-[#d6a954] shadow-[0_0_1.5rem_rgb(214_169_84_/_55%)] motion-reduce:animate-none",
    "user-speaking": "bg-[#d6a954] shadow-[0_0_1.75rem_rgb(214_169_84_/_65%)]",
  }[interaction.state];

  return (
    <div className="pointer-events-none absolute right-0 bottom-[clamp(1.5rem,3.5vh,3.5rem)] left-0 z-50 flex flex-col items-center px-6">
      <div
        className="max-w-[min(90vw,52rem)] rounded-full border border-white/10 bg-[#0d0d0f]/88 px-5 py-2 text-center shadow-2xl backdrop-blur-xl"
        role="status"
        aria-live="assertive"
        aria-label={
          interaction.action === AGENT_INTERACTION_ACTION
            ? "Cortex Home / Voice answer"
            : "Cortex Home / Microphone"
        }
      >
        <span className="text-xs font-bold tracking-[0.18em] text-[#f1d18b] uppercase">
          {title}
        </span>
        <span className="ml-3 text-xs text-[#bdb5a6]">
          {interaction.message || defaultMessage}
        </span>
      </div>
      <div
        className="mt-3 flex h-2 w-[min(76vw,88rem)] items-center justify-center"
        aria-hidden="true"
      >
        <span
          className={cn(
            "block h-1.5 rounded-full transition-[width,background-color,box-shadow] duration-75 ease-out motion-reduce:transition-none",
            tone,
          )}
          style={{ width: `${width}%` }}
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
    <div className="pointer-events-none absolute right-0 bottom-[clamp(7rem,13vh,11rem)] left-0 z-50 flex justify-center px-6">
      <p className="max-w-[min(90vw,58rem)] rounded-lg bg-black/65 px-5 py-2 text-center text-[clamp(1.25rem,2.4vw,2.5rem)] font-bold leading-snug text-[#fff8e8] shadow-[0_2px_2px_black,0_0_3px_black]">
        {text}
      </p>
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
      className="pointer-events-none absolute bottom-[clamp(6.5rem,12vh,10rem)] left-[clamp(1rem,3vw,3rem)] z-[60] w-[min(29rem,calc(100vw-2rem))] rounded-2xl border border-[#d6a954]/25 bg-[#0a0908]/94 p-5 font-mono text-xs text-[#d8ccb6] shadow-2xl backdrop-blur-xl"
      aria-label="Voice diagnostics"
    >
      <div className="mb-4 flex items-center justify-between gap-4 border-white/10 border-b pb-3">
        <div>
          <p className="font-bold tracking-[0.16em] text-[#f1d18b] uppercase">
            Voice diagnostics
          </p>
          <p className="mt-1 text-[#81786a]">Content-free · Ctrl Alt D to hide</p>
        </div>
        <span className="rounded-full bg-[#d6a954]/12 px-3 py-1 text-[#e9c77f] uppercase">
          {metrics.phase || "idle"}
        </span>
      </div>
      <dl className="grid grid-cols-[1fr_auto] gap-x-5 gap-y-2">
        {rows.map(([label, value]) => (
          <div className="contents" key={label}>
            <dt className="text-[#928879]">{label}</dt>
            <dd className="text-right text-[#f1e6d1] tabular-nums">{value}</dd>
          </div>
        ))}
      </dl>
    </aside>
  );
}

function ChannelToast({ interaction }) {
  if (interaction.action !== CHANNEL_ACTION || interaction.state === "idle") {
    return null;
  }

  const copy = interactionCopy[CHANNEL_ACTION][interaction.state];
  if (!copy) {
    return null;
  }
  const [title, defaultMessage] = copy;
  const tone = {
    completed: "border-[#92d6a1]/40 text-[#d8f0d9]",
    failed: "border-[#e67d6f]/40 text-[#ffd4cc]",
    working: "border-[#e9bd68]/40 text-[#f7dfaa]",
  }[interaction.state];

  return (
    <div
      className={cn(
        "absolute top-[clamp(6.5rem,10vw,9rem)] right-[clamp(1.5rem,4vw,5rem)] z-40 max-w-[min(22rem,calc(100vw-3rem))] rounded-2xl border bg-[#17130f]/95 px-5 py-4 shadow-2xl backdrop-blur-xl",
        tone,
      )}
      role="status"
      aria-live="assertive"
    >
      <p className="text-sm font-bold tracking-[0.14em] uppercase">{title}</p>
      <p className="mt-1 text-sm leading-snug text-[#c9bda6]">
        {interaction.message || defaultMessage}
      </p>
    </div>
  );
}

export function RoomFeedback({
  connection,
  lighting,
  interaction,
  subtitle,
  showLightingStatus,
  voiceDebug,
  voiceDebugVisible = false,
  voiceOnly = false,
}) {
  return (
    <>
      {!voiceOnly && <ConnectionNotice connection={connection} />}
      {!voiceOnly && showLightingStatus && <LightingStatus lighting={lighting} />}
      {!voiceOnly && <ChannelToast interaction={interaction} />}
      {!voiceOnly && <InteractionOverlay interaction={interaction} />}
      <VoiceDebugPanel debug={voiceDebug} visible={voiceDebugVisible} />
      <VoiceSubtitles text={subtitle} />
      <VoiceCaptureBar interaction={interaction} />
    </>
  );
}
