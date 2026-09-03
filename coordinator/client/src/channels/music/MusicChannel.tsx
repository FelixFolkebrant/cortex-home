import { useEffect, useRef, useState } from "react";
import { cn } from "../../shared/classes";
import { FALLBACK_MUSIC_PALETTE, paletteFromImage } from "./music-palette";
import { artworkSource, formatTime, projectPosition } from "./music-state";

const FULLSCREEN_TRANSITION_MS = 400;
const FULLSCREEN_ITEM_GRACE_MS = 800;
const artworkPaletteCache = new Map();

function cacheArtworkPalette(source, palette) {
  if (artworkPaletteCache.size >= 32) {
    artworkPaletteCache.delete(artworkPaletteCache.keys().next().value);
  }
  artworkPaletteCache.set(source, palette);
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

function useArtworkPalette(item) {
  const source = artworkSource(item);
  const [loaded, setLoaded] = useState({
    source: null,
    palette: null,
    resolved: false,
  });

  useEffect(() => {
    if (!source) {
      return undefined;
    }

    if (artworkPaletteCache.has(source)) {
      setLoaded({
        source,
        palette: artworkPaletteCache.get(source),
        resolved: true,
      });
      return undefined;
    }

    let active = true;
    const image = new Image();
    image.crossOrigin = "anonymous";
    image.onload = () => {
      if (!active) {
        return;
      }

      let palette = null;
      try {
        palette = paletteFromImage(image);
      } catch {
        // An unreadable cross-origin canvas uses the normal fallback palette.
      }
      cacheArtworkPalette(source, palette);
      setLoaded({ source, palette, resolved: true });
    };
    image.onerror = () => {
      if (!active) {
        return;
      }
      cacheArtworkPalette(source, null);
      setLoaded({ source, palette: null, resolved: true });
    };
    image.src = source;

    return () => {
      active = false;
      image.onload = null;
      image.onerror = null;
    };
  }, [source]);

  if (!source) {
    return { palette: null, resolved: true };
  }
  if (loaded.source === source) {
    return loaded;
  }
  if (artworkPaletteCache.has(source)) {
    return {
      palette: artworkPaletteCache.get(source),
      resolved: true,
    };
  }
  return { palette: null, resolved: false };
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
      <div className="relative z-10 aspect-square w-full overflow-hidden rounded-[clamp(1rem,1.8vw,2rem)] border border-white/10 bg-[#201b15] shadow-[0_2.5rem_8rem_rgb(0_0_0_/_48%)] after:pointer-events-none after:absolute after:inset-0 after:content-[''] after:shadow-[inset_0_0_0_1px_rgb(255_255_255_/_8%),inset_0_-4rem_8rem_rgb(0_0_0_/_12%)]">
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
            className="grid h-full w-full place-items-center bg-[radial-gradient(circle_at_center,transparent_0_19%,#d6a95412_19.2%_19.7%,transparent_20%),repeating-radial-gradient(circle_at_center,#2b251d_0,#2b251d_2px,#1b1712_3px,#1b1712_7px)]"
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
        className="block h-1.5 w-full appearance-none overflow-hidden rounded-full border-0 bg-[rgb(244_234_213_/_15%)] [&::-moz-progress-bar]:rounded-full [&::-moz-progress-bar]:bg-[#f3d18a] [&::-moz-progress-bar]:shadow-[0_0_1.5rem_rgb(243_209_138_/_45%)] [&::-moz-progress-bar]:transition-[width] [&::-moz-progress-bar]:duration-700 [&::-moz-progress-bar]:ease-linear [&::-webkit-progress-bar]:rounded-full [&::-webkit-progress-bar]:bg-[rgb(244_234_213_/_15%)] [&::-webkit-progress-value]:rounded-full [&::-webkit-progress-value]:bg-[#f3d18a] [&::-webkit-progress-value]:shadow-[0_0_1.5rem_rgb(243_209_138_/_45%)] [&::-webkit-progress-value]:transition-[width] [&::-webkit-progress-value]:duration-700 [&::-webkit-progress-value]:ease-linear motion-reduce:[&::-moz-progress-bar]:transition-none motion-reduce:[&::-webkit-progress-value]:transition-none"
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

function SpotifySource() {
  return (
    <div className="inline-flex items-center gap-3 text-[clamp(1rem,1.2vw,1.25rem)] font-bold tracking-[-0.02em] text-[#e8ddc8]">
      <span className="sr-only">Playback source:</span>
      <svg
        aria-hidden="true"
        className="h-[1.5em] w-[1.5em] shrink-0"
        viewBox="0 0 24 24"
      >
        <circle cx="12" cy="12" r="12" fill="#1ed760" />
        <path
          d="M5.8 8.9c4.1-1.2 8.8-.9 12.4.9M6.7 12.3c3.5-1 7.5-.7 10.6.8M7.5 15.5c2.9-.8 6.1-.6 8.7.7"
          fill="none"
          stroke="#101010"
          strokeLinecap="round"
          strokeWidth="1.65"
        />
      </svg>
      <span>Spotify</span>
    </div>
  );
}

function LoadedMusic({ playback }) {
  const { item } = playback;

  return (
    <main className="relative z-10 grid min-h-screen items-center gap-[clamp(3rem,6vw,8rem)] px-[clamp(2rem,6vw,8rem)] py-[clamp(2rem,5vh,5rem)] md:grid-cols-[minmax(20rem,0.88fr)_minmax(0,1.12fr)]">
      <section className="relative mx-auto w-full max-w-[42rem]">
        <Artwork item={item} />
      </section>

      <section className="min-w-0">
        <div className="mb-[clamp(1.5rem,3vh,3rem)]">
          <SpotifySource />
        </div>

        <h1 className="line-clamp-3 max-w-[12ch] text-[clamp(3.5rem,6.2vw,8rem)] leading-[0.88] font-bold tracking-[-0.065em] text-[#fff7e7]">
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
  if (playback?.status === "stopped") {
    return (
      <main className="relative z-10 grid min-h-screen place-content-center px-[8vw] text-center">
        <div className="mb-8 flex justify-center">
          <SpotifySource />
        </div>
        <h1 className="mx-auto max-w-[18ch] text-[clamp(3rem,6vw,7rem)] leading-[0.92] font-bold tracking-[-0.06em] text-[#fff7e7]">
          Choose &quot;Högtalaren&quot; as speaker in Spotify to connect
        </h1>
      </main>
    );
  }

  let title = "Loading the room.";
  let message = "Waiting for the first playback observation.";
  let label = "Connecting";

  if (playback?.status === "unavailable") {
    title = "Receiver unavailable.";
    message = "Högtalaren will report again after the next receiver event.";
    label = "Unavailable";
  } else if (connection === "connecting") {
    title = "Finding the room.";
    message = "Connecting to the coordinator.";
  }

  return (
    <main className="relative z-10 grid min-h-screen place-content-center px-[8vw] text-center">
      <div className="mb-8 flex justify-center">
        <SpotifySource />
      </div>
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

function FullscreenArtwork({ item }) {
  const source = artworkSource(item);

  return (
    <div className="absolute top-1/2 left-1/2 h-[var(--music-artwork-size)] w-[var(--music-artwork-size)] -translate-x-1/2 -translate-y-1/2 overflow-hidden bg-[var(--music-background)]">
      {source && (
        <img
          key={source}
          className="h-full w-full object-cover"
          src={source}
          alt={`Artwork for ${item.title}`}
          referrerPolicy="no-referrer"
          onError={(event) => {
            event.currentTarget.hidden = true;
          }}
        />
      )}
    </div>
  );
}

function dimmedMonochrome(color, opacity) {
  const channel = color === "#000000" ? 0 : 255;
  return `rgb(${channel} ${channel} ${channel} / ${opacity}%)`;
}

function ProgressiveTitle({
  children = "",
  className,
  progress,
  accent,
  titleElement: Title,
}) {
  const titleFit = Math.max(7, [...children].length * 0.56);

  return (
    <Title
      aria-label={`${children}, ${Math.round(progress)} percent complete`}
      className={cn(
        "max-w-full flex-none overflow-hidden bg-[linear-gradient(90deg,var(--music-accent)_0%,var(--music-accent)_var(--music-progress),var(--music-unplayed)_var(--music-progress),var(--music-unplayed)_100%)] bg-clip-text font-bold tracking-[-0.065em] leading-[0.82] text-ellipsis text-transparent",
        className,
      )}
      style={{
        "--music-accent": accent,
        "--music-current-title-size": `${76 / titleFit}svh`,
        "--music-next-title-size": `${42 / titleFit}svh`,
        "--music-progress": `${progress}%`,
      }}
    >
      {children}
    </Title>
  );
}

function FullscreenMetadata({
  className,
  copyClassName,
  detailsClassName,
  item,
  palette,
  progress,
  titleClassName,
  titleElement,
}) {
  return (
    <section className={className}>
      <div
        className={cn(
          "absolute left-1/2 flex -translate-x-1/2 -translate-y-1/2 rotate-[-90deg] transform flex-col items-start gap-[clamp(0.5rem,0.8vw,1rem)] origin-center whitespace-nowrap",
          copyClassName,
        )}
        style={{
          "--music-artist": dimmedMonochrome(palette.dim, 40),
          "--music-unplayed": dimmedMonochrome(palette.dim, 60),
        }}
      >
        <ProgressiveTitle
          className={titleClassName}
          progress={progress}
          accent={palette.accent}
          titleElement={titleElement}
        >
          {item.title}
        </ProgressiveTitle>
        <p className={detailsClassName}>{item.creators.join(", ")}</p>
      </div>
    </section>
  );
}

export function updateFullscreenTracks(tracks, playback) {
  if (!playback?.item) {
    return tracks;
  }
  if (!tracks.current) {
    return { ...tracks, current: playback };
  }
  if (tracks.current.item.uri === playback.item.uri) {
    return { ...tracks, current: playback };
  }
  return {
    current: playback,
    outgoing: tracks.current,
    generation: tracks.generation + 1,
  };
}

function FullscreenTrack({
  playback,
  palette,
  phase,
}: {
  key?: string;
  playback: any;
  palette: any;
  phase: string;
}) {
  const { item, nextItem } = playback;
  const position = useProjectedPosition(playback);
  const nextArtworkPalette = useArtworkPalette(nextItem).palette;

  const progress = Math.min(100, (position / item.durationMs) * 100);
  const remaining = Math.max(0, item.durationMs - position);
  const showNext = nextItem && remaining <= 10_000;
  const nextProgress = Math.min(100, ((10_000 - remaining) / 10_000) * 100);
  const trackClassName = {
    current: "z-[2]",
    incoming:
      "z-[3] animate-[music-track-enter_400ms_cubic-bezier(0.7,0,0.3,1)_both] motion-reduce:animate-none",
    outgoing:
      "z-[2] animate-[music-track-exit_400ms_cubic-bezier(0.7,0,0.3,1)_both] motion-reduce:animate-none",
  }[phase];

  return (
    <div
      aria-hidden={phase === "outgoing" || undefined}
      className={cn("absolute inset-0 overflow-hidden", trackClassName)}
      style={{ "--music-background": palette.background }}
    >
      <FullscreenArtwork item={item} />
      <FullscreenMetadata
        className="pointer-events-none absolute inset-y-0 left-0 w-[max(calc((100vw-var(--music-artwork-size))/2),14rem)] overflow-hidden"
        copyClassName="top-1/2 w-[min(78svh,58rem)]"
        detailsClassName="text-[clamp(1.2rem,1.65vw,2rem)] font-normal tracking-[-0.035em] leading-none"
        item={item}
        palette={palette}
        progress={progress}
        titleClassName="text-[clamp(3.2rem,min(var(--music-current-title-size),6.2vw),7.5rem)]"
        titleElement="h1"
      />
      {showNext && (
        <FullscreenMetadata
          className="pointer-events-none absolute inset-y-0 right-0 w-[max(calc((100vw-var(--music-artwork-size))/2),14rem)] overflow-hidden"
          copyClassName="top-[clamp(1.5rem,4vh,3rem)] w-[min(46svh,32rem)]"
          detailsClassName="text-[clamp(0.9rem,1vw,1.25rem)] font-normal tracking-[-0.025em] leading-none"
          item={nextItem}
          palette={{
            accent: nextArtworkPalette?.accent || palette.dim,
            dim: palette.dim,
          }}
          progress={nextProgress}
          titleClassName="text-[clamp(2.1rem,min(var(--music-next-title-size),3.7vw),4.5rem)] tracking-[-0.055em]"
          titleElement="h2"
        />
      )}
    </div>
  );
}

export function MusicFullscreen({ playback }) {
  const [tracks, setTracks] = useState(() =>
    updateFullscreenTracks({ current: null, outgoing: null, generation: 0 }, playback),
  );
  const currentPaletteResult = useArtworkPalette(tracks.current?.item);
  const outgoingPaletteResult = useArtworkPalette(tracks.outgoing?.item);
  const lastBackground = useRef(FALLBACK_MUSIC_PALETTE.background);

  useEffect(() => {
    setTracks((current) => updateFullscreenTracks(current, playback));
  }, [playback]);

  useEffect(() => {
    if (!tracks.outgoing) {
      return undefined;
    }

    const generation = tracks.generation;
    const timer = window.setTimeout(() => {
      setTracks((current) =>
        current.generation === generation ? { ...current, outgoing: null } : current,
      );
    }, FULLSCREEN_TRANSITION_MS);
    return () => window.clearTimeout(timer);
  }, [tracks.generation, tracks.outgoing]);

  useEffect(() => {
    if (playback?.item || !tracks.current) {
      return undefined;
    }

    const retainedUri = tracks.current.item.uri;
    const timer = window.setTimeout(() => {
      setTracks((current) =>
        current.current?.item.uri === retainedUri
          ? { ...current, current: null, outgoing: null }
          : current,
      );
    }, FULLSCREEN_ITEM_GRACE_MS);
    return () => window.clearTimeout(timer);
  }, [playback?.item, tracks.current]);

  const currentPalette = currentPaletteResult.palette || FALLBACK_MUSIC_PALETTE;
  const outgoingPalette = outgoingPaletteResult.palette || FALLBACK_MUSIC_PALETTE;
  if (currentPaletteResult.resolved) {
    lastBackground.current = currentPalette.background;
  }

  return (
    <main
      aria-label="Music fullscreen view"
      className="relative h-[100svh] w-screen overflow-hidden [--music-artwork-size:min(100vw,100svh)] bg-[var(--music-background,#0c0d0e)] transition-[background-color] duration-[400ms] ease-[cubic-bezier(0.7,0,0.3,1)] motion-reduce:transition-none"
      style={{ "--music-background": lastBackground.current }}
    >
      {tracks.outgoing && (
        <FullscreenTrack
          key={tracks.outgoing.item.uri}
          playback={tracks.outgoing}
          palette={outgoingPalette}
          phase="outgoing"
        />
      )}
      {tracks.current && (
        <FullscreenTrack
          key={tracks.current.item.uri}
          playback={tracks.current}
          palette={currentPalette}
          phase={tracks.outgoing ? "incoming" : "current"}
        />
      )}
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
