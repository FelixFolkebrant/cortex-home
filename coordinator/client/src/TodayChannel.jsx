import { useEffect, useState } from "react";

const conditionLabels = {
  clear: "Clear",
  cloudy: "Cloudy",
  fog: "Fog",
  partly_cloudy: "Partly cloudy",
  rain: "Rain",
  sleet: "Sleet",
  snow: "Snow",
  thunderstorm: "Thunderstorms",
  unknown: "Weather unavailable",
};

function useLocalTime(timeZone) {
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  return {
    date: new Intl.DateTimeFormat("en-GB", {
      dateStyle: "full",
      timeZone,
    }).format(now),
    time: new Intl.DateTimeFormat("en-GB", {
      hour: "2-digit",
      minute: "2-digit",
      timeZone,
    }).format(now),
  };
}

export function TodayChannel({ summary }) {
  const timeZone = summary?.timeZone || "Europe/Stockholm";
  const { date, time } = useLocalTime(timeZone);
  const isAvailable = summary?.status === "available";

  return (
    <main className="relative z-10 flex min-h-screen flex-col px-[clamp(2rem,6vw,8rem)] py-[clamp(2rem,5vh,5rem)]">
      <div className="flex flex-wrap items-center justify-between gap-5 text-[clamp(0.8rem,1vw,1.05rem)] font-bold tracking-[0.22em] text-[#d6a954] uppercase">
        <span>Cortex Home / Today</span>
        <span className="text-[#9d9382]">Linköping</span>
      </div>

      <section className="my-auto py-[clamp(3rem,8vh,8rem)]">
        <p className="text-[clamp(1.2rem,2vw,2.4rem)] font-medium tracking-[-0.025em] text-[#c9bda6]">
          {date}
        </p>
        <h1 className="mt-3 text-[clamp(6rem,17vw,18rem)] leading-[0.78] font-bold tracking-[-0.09em] text-[#fff7e7] tabular-nums">
          {time}
        </h1>

        {isAvailable ? (
          <div className="mt-[clamp(3rem,7vh,7rem)] flex flex-wrap items-end gap-x-8 gap-y-3">
            <span className="text-[clamp(4rem,9vw,10rem)] leading-none font-bold tracking-[-0.08em] text-[#efc66f] tabular-nums">
              {summary.current.temperatureC}°
            </span>
            <span className="pb-2 text-[clamp(1.5rem,2.8vw,3.5rem)] font-medium tracking-[-0.04em] text-[#e1d4bd]">
              {conditionLabels[summary.current.condition] || conditionLabels.unknown}
            </span>
          </div>
        ) : (
          <p className="mt-[clamp(3rem,7vh,7rem)] text-[clamp(1.5rem,2.8vw,3.5rem)] font-medium tracking-[-0.04em] text-[#c9bda6]">
            Weather is unavailable.
          </p>
        )}
      </section>

      {isAvailable && (
        <section
          aria-label="Three-day forecast"
          className="grid grid-cols-3 gap-3 sm:gap-6"
        >
          {summary.forecast.map((day) => (
            <article
              className="rounded-[clamp(1rem,1.8vw,2rem)] border border-white/10 bg-[#201b15]/70 p-[clamp(1rem,2vw,2rem)]"
              key={day.date}
            >
              <p className="text-[clamp(0.75rem,1vw,1rem)] font-bold tracking-[0.18em] text-[#d6a954] uppercase">
                {new Intl.DateTimeFormat("en-GB", {
                  weekday: "short",
                  timeZone,
                }).format(new Date(`${day.date}T12:00:00Z`))}
              </p>
              <p className="mt-4 text-[clamp(1.15rem,2vw,2.3rem)] font-medium tracking-[-0.04em] text-[#f0e4ce]">
                {conditionLabels[day.condition] || conditionLabels.unknown}
              </p>
              <p className="mt-5 text-[clamp(1.1rem,1.8vw,2rem)] font-bold tracking-[-0.05em] text-[#c9bda6] tabular-nums">
                {day.highC}° <span className="text-[#837968]">/ {day.lowC}°</span>
              </p>
            </article>
          ))}
        </section>
      )}

      <p className="mt-7 text-xs tracking-[0.12em] text-[#756d60]">
        Weather data: MET Norway · CC BY 4.0
      </p>
    </main>
  );
}
