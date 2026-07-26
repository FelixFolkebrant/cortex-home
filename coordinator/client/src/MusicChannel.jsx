import { useEffect, useState } from "react";
import { cn } from "./classes";
import { artworkSource, formatTime, projectPosition } from "./room-state";

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

export function MusicChannel({ playback, connection }) {
  return playback?.item ? (
    <LoadedMusic playback={playback} />
  ) : (
    <EmptyMusic playback={playback} connection={connection} />
  );
}
