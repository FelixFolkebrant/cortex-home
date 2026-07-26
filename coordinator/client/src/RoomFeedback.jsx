import { cva } from "class-variance-authority";
import { cn } from "./classes";
import { CHANNEL_ACTION, IDENTIFY_ACTION, SCENE_ACTION } from "./room-state";

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
  if (interaction.state === "idle" || interaction.action === CHANNEL_ACTION) {
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

export function RoomFeedback({ connection, lighting, interaction }) {
  return (
    <>
      <ConnectionNotice connection={connection} />
      <LightingStatus lighting={lighting} />
      <ChannelToast interaction={interaction} />
      <InteractionOverlay interaction={interaction} />
    </>
  );
}
