import { useEffect, useRef, useState } from "react";
import { cn } from "../shared/classes";
import { FALLBACK_MUSIC_PALETTE, paletteFromImage } from "./music-palette";
import { artworkSource, projectPosition } from "./music-state";

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
