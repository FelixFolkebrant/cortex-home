import { cva } from "class-variance-authority";
import { useEffect, useReducer, useRef, useState } from "react";
import { cn } from "./classes";
import {
  artworkSource,
  formatTime,
  initialRoomState,
  projectPosition,
  roomReducer,
} from "./music";

const interactionCopy = {
  identifying: ["Here I am.", "Playing the room signal."],
  completed: ["Identified.", "The room confirmed the request."],
  failed: ["Couldn’t identify.", "The request failed."],
};

const signal = cva(
  "mx-auto mt-12 aspect-square w-[clamp(7rem,12vw,12rem)] rounded-full border-2 transition-[border-color,box-shadow,transform] duration-300 motion-reduce:animate-none motion-reduce:transition-none",
  {
    variants: {
      state: {
        identifying:
          "animate-identify border-[#ffd27d] shadow-[0_0_0_2rem_rgb(255_210_125_/_16%),0_0_9rem_rgb(255_177_63_/_70%)]",
        completed:
          "scale-[1.08] border-[#92d6a1] shadow-[0_0_0_1.5rem_rgb(146_214_161_/_14%),0_0_7rem_rgb(146_214_161_/_45%)]",
        failed:
          "border-[#e67d6f] shadow-[0_0_0_1.5rem_rgb(230_125_111_/_12%),0_0_6rem_rgb(230_125_111_/_38%)]",
      },
    },
  },
);

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

function useProjectedPosition(playback) {
  const [now, setNow] = useState(Date.now());

  useEffect(() => {
    setNow(Date.now());
    if (playback?.status !== "playing" || !playback.item) {
      return undefined;
    }

    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [playback]);

  return projectPosition(playback, now);
}

function Artwork({ item }) {
  const source = artworkSource(item);
  const [failedSource, setFailedSource] = useState(null);
  const showArtwork = source && failedSource !== source;

  return (
    <>
      {showArtwork && (
        <img
          aria-hidden="true"
          className="pointer-events-none absolute inset-[-8%] h-[116%] w-[116%] scale-110 object-cover opacity-20 blur-[90px] saturate-75"
          src={source}
          alt=""
          referrerPolicy="no-referrer"
          onError={() => setFailedSource(source)}
        />
      )}
      <div className="artwork-frame relative z-10 aspect-square w-full overflow-hidden rounded-[clamp(1rem,1.8vw,2rem)] border border-white/10 bg-[#201b15] shadow-[0_2.5rem_8rem_rgb(0_0_0_/_48%)]">
        {showArtwork ? (
          <img
            className="h-full w-full object-cover"
            src={source}
            alt={`Artwork for ${item.title}`}
            referrerPolicy="no-referrer"
            onError={() => setFailedSource(source)}
          />
        ) : (
          <div
            className="record-grooves grid h-full w-full place-items-center"
            role="img"
            aria-label={`Artwork unavailable for ${item.title}`}
          >
            <div className="grid aspect-square w-[38%] place-items-center rounded-full border border-[#d6a954]/35 bg-[#16130f] shadow-[0_0_4rem_rgb(214_169_84_/_18%)]">
              <span className="text-[clamp(1rem,2vw,2rem)] font-bold tracking-[0.3em] text-[#d6a954]">
                CH
              </span>
            </div>
          </div>
        )}
      </div>
    </>
  );
}

function PlaybackProgress({ playback }) {
  const position = useProjectedPosition(playback);
  const duration = playback.item.durationMs;

  return (
    <div className="mt-[clamp(2rem,5vh,5rem)] max-w-[54rem]">
      <progress
        className="playback-progress block h-1.5 w-full overflow-hidden rounded-full"
        value={position}
        max={duration}
        aria-label={`Playback progress: ${formatTime(position)} of ${formatTime(duration)}`}
      />
      <div className="mt-4 flex justify-between font-mono text-[clamp(0.95rem,1.2vw,1.25rem)] tracking-[0.08em] text-[#c9bda6] tabular-nums">
        <span>{formatTime(position)}</span>
        <span>{formatTime(duration)}</span>
      </div>
    </div>
  );
}

function LoadedMusic({ playback }) {
  const { item, status } = playback;
  const statusLabel = status === "paused" ? "Paused" : "Now playing";
  const typeLabel = item.type === "episode" ? "Episode" : "Music";

  return (
    <main className="relative z-10 grid min-h-screen items-center gap-[clamp(3rem,6vw,8rem)] px-[clamp(2rem,6vw,8rem)] py-[clamp(2rem,5vh,5rem)] md:grid-cols-[minmax(20rem,0.88fr)_minmax(0,1.12fr)]">
      <section className="relative mx-auto w-full max-w-[42rem]">
        <Artwork item={item} />
      </section>

      <section className="min-w-0">
        <div className="mb-[clamp(1.5rem,3vh,3rem)] flex flex-wrap items-center gap-4 text-[clamp(0.8rem,1vw,1.05rem)] font-bold tracking-[0.22em] uppercase">
          <span className="text-[#d6a954]">Cortex Home</span>
          <span aria-hidden="true" className="h-px w-10 bg-[#d6a954]/50" />
          <span className="flex items-center gap-3 text-[#e8ddc8]">
            <span
              className={cn(
                "h-2.5 w-2.5 rounded-full",
                status === "playing"
                  ? "bg-[#efc66f] shadow-[0_0_1rem_rgb(239_198_111_/_75%)]"
                  : "bg-[#a89f8f]",
              )}
            />
            {statusLabel}
          </span>
          <span className="text-[#8f8677]">/ {typeLabel}</span>
        </div>

        <h1 className="music-title max-w-[12ch] text-[clamp(3.5rem,6.2vw,8rem)] leading-[0.88] font-bold tracking-[-0.065em] text-[#fff7e7]">
          {item.title}
        </h1>
        <p className="mt-[clamp(1.5rem,3vh,3rem)] text-[clamp(1.5rem,2.4vw,3rem)] leading-tight font-medium tracking-[-0.025em] text-[#e1d4bd]">
          {item.creators.join(", ")}
        </p>
        <p className="mt-3 max-w-[42ch] truncate text-[clamp(1rem,1.35vw,1.5rem)] text-[#948a79]">
          {item.collection}
        </p>
        <PlaybackProgress playback={playback} />
      </section>
    </main>
  );
}

function EmptyMusic({ playback, connection }) {
  let title = "Loading the room.";
  let message = "Waiting for the first playback observation.";
  let label = "Connecting";

  if (playback?.status === "stopped") {
    title = "Playback stopped.";
    message = "Choose Högtalaren in Spotify when the room needs music.";
    label = "Stopped";
  } else if (playback?.status === "unavailable") {
    title = "Receiver unavailable.";
    message = "Högtalaren will report again after the next receiver event.";
    label = "Unavailable";
  } else if (connection === "connecting") {
    title = "Finding the room.";
    message = "Connecting to the coordinator.";
  }

  return (
    <main className="relative z-10 grid min-h-screen place-content-center px-[8vw] text-center">
      <p className="mb-8 text-[clamp(0.9rem,1.2vw,1.2rem)] font-bold tracking-[0.28em] text-[#d6a954] uppercase">
        Cortex Home / Music
      </p>
      <h1 className="mx-auto max-w-[12ch] text-[clamp(4.5rem,9vw,10rem)] leading-[0.88] font-bold tracking-[-0.07em] text-[#fff7e7]">
        {title}
      </h1>
      <p className="mx-auto mt-10 max-w-[42ch] text-[clamp(1.2rem,2vw,2rem)] leading-relaxed text-[#b9ad98]">
        {message}
      </p>
      <p className="mt-14 text-sm font-bold tracking-[0.24em] text-[#756d60] uppercase">
        {label}
      </p>
    </main>
  );
}

function ConnectionNotice({ connection }) {
  if (connection !== "disconnected") {
    return null;
  }

  return (
    <div
      className="absolute top-[clamp(1.5rem,3vw,3rem)] right-[clamp(1.5rem,4vw,5rem)] z-30 flex items-center gap-3 rounded-full border border-[#e9bd68]/30 bg-[#17130f]/90 px-5 py-3 text-sm font-bold tracking-[0.12em] text-[#f0d79d] uppercase shadow-2xl backdrop-blur-xl"
      role="status"
    >
      <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-[#e9bd68] motion-reduce:animate-none" />
      Coordinator offline · Reconnecting
    </div>
  );
}

function InteractionOverlay({ interaction }) {
  if (interaction.state === "idle") {
    return null;
  }

  const [title, defaultMessage] = interactionCopy[interaction.state];

  return (
    <div
      className="absolute inset-0 z-40 grid place-content-center bg-[#120f0c]/88 px-[8vw] text-center backdrop-blur-2xl"
      role="status"
      aria-live="assertive"
    >
      <p className="mb-7 text-[clamp(0.85rem,1vw,1.1rem)] font-bold tracking-[0.28em] text-[#d6a954] uppercase">
        Cortex Home / Room signal
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

export function App() {
  const [room, dispatch] = useReducer(roomReducer, initialRoomState);
  const currentClientEntry = document
    .querySelector('script[type="module"][src]')
    ?.getAttribute("src");
  const endpointToken = useRef(null);
  const activeRequestId = useRef(null);
  const actionGeneration = useRef(0);
  const interactionTimer = useRef(null);

  useEffect(() => {
    function clearInteractionTimer() {
      if (interactionTimer.current) {
        window.clearTimeout(interactionTimer.current);
        interactionTimer.current = null;
      }
    }

    function showInteraction(state, message, duration) {
      clearInteractionTimer();
      dispatch({ type: "interaction", state, message });

      if (duration) {
        interactionTimer.current = window.setTimeout(() => {
          dispatch({ type: "interaction", state: "idle" });
          interactionTimer.current = null;
        }, duration);
      }
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
      showInteraction("identifying");

      try {
        await postStatus(requestId, "identifying");
        await playIdentifySound();

        if (generation !== actionGeneration.current) {
          return;
        }

        await postStatus(requestId, "completed");
        activeRequestId.current = null;
        showInteraction("completed", null, 2500);
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
        showInteraction("failed", message, 5000);
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
      activeRequestId.current = null;
      clearInteractionTimer();
      dispatch({ type: "connection", state: "connected" });
      dispatch({ type: "interaction", state: "idle" });
    });

    events.addEventListener("music.playback", (event) => {
      const snapshot = parseMessage(event);
      if (snapshot) {
        dispatch({ type: "playback", snapshot });
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
        showInteraction("failed", message.error, 5000);
      }
    });

    events.onerror = () => {
      endpointToken.current = null;
      actionGeneration.current += 1;
      activeRequestId.current = null;
      clearInteractionTimer();
      dispatch({ type: "connection", state: "disconnected" });
      dispatch({ type: "interaction", state: "idle" });
    };

    return () => {
      clearInteractionTimer();
      events.close();
    };
  }, [currentClientEntry]);

  const hasLoadedItem = Boolean(room.playback?.item);

  return (
    <div className="relative min-h-screen overflow-hidden bg-[#120f0c] text-[#f8f0dc]">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_22%_42%,rgb(111_78_37_/_22%)_0,transparent_34%),radial-gradient(circle_at_78%_68%,rgb(67_51_34_/_18%)_0,transparent_40%),linear-gradient(135deg,#17130f_0%,#0f0d0a_100%)]"
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 opacity-[0.16] [background-image:linear-gradient(rgb(255_255_255_/_5%)_1px,transparent_1px),linear-gradient(90deg,rgb(255_255_255_/_5%)_1px,transparent_1px)] [background-size:4rem_4rem] [mask-image:linear-gradient(to_bottom,black,transparent_85%)]"
      />

      {hasLoadedItem ? (
        <LoadedMusic playback={room.playback} />
      ) : (
        <EmptyMusic playback={room.playback} connection={room.connection} />
      )}

      <ConnectionNotice connection={room.connection} />
      <InteractionOverlay interaction={room.interaction} />
    </div>
  );
}
