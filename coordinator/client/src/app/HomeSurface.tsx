import { useEffect, useState } from "react";
import alarmIcon from "../assets/alarm.svg";
import weatherArtwork from "../assets/home-weather.png";
import { artworkSource, projectPosition } from "../music/music-state";

function useLocalTime(timeZone) {
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  return {
    date: new Intl.DateTimeFormat("en-GB", {
      day: "numeric",
      month: "long",
      timeZone,
    })
      .format(now)
      .toLocaleLowerCase("en-GB"),
    time: new Intl.DateTimeFormat("en-GB", {
      hour: "2-digit",
      minute: "2-digit",
      timeZone,
    }).format(now),
  };
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

function NowPlaying({ playback }) {
  const item = playback?.item;
  const position = useProjectedPosition(playback);
  if (!item) {
    return null;
  }

  const artwork = artworkSource(item);
  const progress = item.durationMs
    ? Math.min(100, Math.max(0, (position / item.durationMs) * 100))
    : 0;

  return (
    <aside
      aria-label={`Now playing ${item.title} by ${item.creators.join(", ")}`}
      className="absolute top-[4.8%] right-[-2.45%] grid h-[clamp(6.7rem,12.6vw,8.9rem)] w-[clamp(22rem,25.2vw,29rem)] grid-cols-[1fr_auto] overflow-hidden rounded-[1.2rem] border border-[#e9e9e9] bg-[#f8f8f8] px-[clamp(1rem,2vw,2.35rem)] py-[clamp(0.7rem,1.3vw,1rem)] text-black shadow-[0_2px_4px_rgb(0_0_0_/_11%)]"
    >
      <div className="flex min-w-0 flex-col items-end justify-center pr-[clamp(1rem,1.7vw,1.9rem)] text-right">
        <p className="max-w-full truncate text-[clamp(0.85rem,1.3vw,1.5rem)] leading-tight text-black/60">
          {item.creators.join(", ")}
        </p>
        <p className="mt-0.5 max-w-full truncate text-[clamp(1.25rem,1.95vw,2.25rem)] leading-tight">
          {item.title}
        </p>
        <div
          aria-hidden="true"
          className="mt-auto h-1.5 w-full max-w-[13.4rem] overflow-hidden rounded-full bg-[#dedede]"
        >
          <span
            className="block h-full rounded-full bg-black transition-[width] duration-700 ease-linear motion-reduce:transition-none"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>
      <div className="aspect-square h-full overflow-hidden bg-[#e8e8e8] shadow-[0_2px_4px_rgb(0_0_0_/_11%)]">
        {artwork ? (
          <img
            alt={`Artwork for ${item.title}`}
            className="h-full w-full object-cover"
            referrerPolicy="no-referrer"
            src={artwork}
          />
        ) : (
          <div
            aria-hidden="true"
            className="h-full w-full bg-[radial-gradient(circle_at_35%_30%,#b7c7d8,#202b36_65%,#0a0d10)]"
          />
        )}
      </div>
    </aside>
  );
}

function AlarmSummary({ alarm }) {
  if (!alarm?.time || !["armed", "ringing"].includes(alarm.status)) {
    return null;
  }

  return (
    <div
      aria-label={`Alarm set for ${alarm.time}`}
      className="flex h-[clamp(3.4rem,6.2vw,4.4rem)] items-center gap-[clamp(0.65rem,1vw,1rem)] rounded-[1.2rem] border border-[#e9e9e9] bg-[#f8f8f8] px-[clamp(1rem,1.4vw,1.4rem)] text-black/20 shadow-[0_2px_4px_rgb(0_0_0_/_11%)]"
      role="status"
    >
      <img
        alt=""
        aria-hidden="true"
        className="h-[clamp(1.6rem,2vw,2.15rem)] w-[clamp(1.8rem,2.2vw,2.35rem)]"
        src={alarmIcon}
      />
      <span className="text-[clamp(1.8rem,3vw,2.55rem)] leading-none tabular-nums">
        {alarm.time}
      </span>
    </div>
  );
}

function CurrentWeather({ summary }) {
  const available = summary?.status === "available";
  const temperature = available ? `${summary.current.temperatureC}°` : "—";

  return (
    <section
      aria-label={
        available ? `Current temperature ${temperature}` : "Weather unavailable"
      }
      className="relative mt-[clamp(2.8rem,5.4vh,3.8rem)] h-[clamp(7.6rem,13.5vh,9.5rem)] w-[clamp(27rem,32.6vw,37.5rem)] overflow-hidden rounded-[1.2rem] border border-[#e9e9e9] shadow-[0_2px_4px_rgb(0_0_0_/_11%)]"
    >
      <img
        alt=""
        aria-hidden="true"
        className="absolute inset-0 h-full w-full object-cover"
        src={weatherArtwork}
      />
      <div aria-hidden="true" className="absolute inset-0 bg-black/20" />
      <p className="relative grid h-full place-content-center text-[clamp(3.6rem,6vw,5rem)] leading-none text-white text-shadow-[0_2px_2px_rgb(0_0_0_/_25%)] tabular-nums">
        {temperature}
      </p>
    </section>
  );
}

export function HomeSurface({ alarm, playback, summary }) {
  const timeZone = summary?.timeZone || "Europe/Stockholm";
  const { date, time } = useLocalTime(timeZone);

  return (
    <main
      aria-label="Home"
      className="relative h-[100svh] min-h-[36rem] w-screen overflow-hidden bg-white font-sans text-black"
    >
      <NowPlaying playback={playback} />

      <div className="absolute top-[19.3%] left-1/2 flex -translate-x-1/2 flex-col items-center">
        <time className="text-[clamp(8rem,15.8vw,11.2rem)] leading-[1.05] font-normal tracking-[-0.065em] text-black/60 tabular-nums">
          {time}
        </time>
        <div className="mt-[clamp(0.4rem,1.3vh,0.9rem)] flex items-center gap-[clamp(1.6rem,3.2vw,3.8rem)]">
          <p className="whitespace-nowrap text-[clamp(1.75rem,3.55vw,2.55rem)] text-black/60">
            {date}
          </p>
          <AlarmSummary alarm={alarm} />
        </div>
        <CurrentWeather summary={summary} />
      </div>
    </main>
  );
}
