import { useEffect, useState } from "react";
import { requestEndpointControl } from "../shared/endpoint-control";

const REFRESH_INTERVAL_MS = 2000;

function finiteNumber(value) {
  return typeof value === "number" && Number.isFinite(value);
}

export function isSystemStatsShortcut(event) {
  return (
    event.code === "KeyM" &&
    event.altKey &&
    event.ctrlKey &&
    !event.metaKey &&
    !event.shiftKey &&
    !event.repeat
  );
}

export function isSystemStatsDismissShortcut(event) {
  return (
    event.key === "Escape" &&
    !event.altKey &&
    !event.ctrlKey &&
    !event.metaKey &&
    !event.shiftKey &&
    !event.repeat
  );
}

export async function requestSystemStats(fetcher = fetch, wait = undefined) {
  let response;

  try {
    response = await requestEndpointControl("/stats", { method: "GET" }, fetcher, wait);
  } catch {
    throw new Error("Computer stats are unavailable.");
  }
  const result = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error("Computer stats are unavailable.");
  }

  const valid =
    finiteNumber(result.cpuPercent) &&
    result.cpuPercent >= 0 &&
    result.cpuPercent <= 100 &&
    finiteNumber(result.memoryPercent) &&
    result.memoryPercent >= 0 &&
    result.memoryPercent <= 100 &&
    Number.isInteger(result.memoryUsedMiB) &&
    result.memoryUsedMiB >= 0 &&
    Number.isInteger(result.memoryTotalMiB) &&
    result.memoryTotalMiB > 0 &&
    result.memoryUsedMiB <= result.memoryTotalMiB &&
    (result.temperatureC === null ||
      (finiteNumber(result.temperatureC) &&
        result.temperatureC >= -50 &&
        result.temperatureC <= 150)) &&
    finiteNumber(result.loadOne) &&
    result.loadOne >= 0 &&
    Number.isInteger(result.uptimeSeconds) &&
    result.uptimeSeconds >= 0;

  if (!valid) {
    throw new Error("Computer stats returned invalid data.");
  }

  return result;
}

function formatUptime(seconds) {
  const days = Math.floor(seconds / 86_400);
  const hours = Math.floor((seconds % 86_400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);

  if (days > 0) {
    return `${days}d ${hours}h`;
  }
  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  }
  return `${minutes}m`;
}

function Stat({ label, value, detail = null }) {
  return (
    <div className="border-white/10 border-t pt-4">
      <dt className="text-xs font-bold tracking-[0.16em] text-[#9f9584] uppercase">
        {label}
      </dt>
      <dd className="mt-2 text-3xl font-bold tracking-[-0.05em] text-[#fff7e7] tabular-nums">
        {value}
      </dd>
      {detail && <p className="mt-1 text-xs text-[#887f71] tabular-nums">{detail}</p>}
    </div>
  );
}

export function SystemStats({ visible, onDismiss }) {
  const [snapshot, setSnapshot] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!visible) {
      return undefined;
    }

    let current = true;
    let timer = null;

    async function refresh() {
      try {
        const nextSnapshot = await requestSystemStats();
        if (current) {
          setSnapshot(nextSnapshot);
          setError(null);
        }
      } catch (requestError) {
        if (current) {
          setError(requestError.message);
        }
      } finally {
        if (current) {
          timer = window.setTimeout(refresh, REFRESH_INTERVAL_MS);
        }
      }
    }

    void refresh();

    return () => {
      current = false;
      if (timer) {
        window.clearTimeout(timer);
      }
    };
  }, [visible]);

  if (!visible) {
    return null;
  }

  return (
    <aside
      aria-keyshortcuts="Control+Alt+M"
      aria-label="Computer performance overview"
      className="pointer-events-none fixed top-[clamp(1rem,3vw,3rem)] right-[clamp(1rem,3vw,3rem)] z-[80] w-[min(31rem,calc(100vw-2rem))] border border-white/15 bg-[#0b0a08] p-[clamp(1.25rem,2.5vw,2rem)] shadow-2xl"
    >
      <div className="flex items-start justify-between gap-6">
        <div>
          <p className="text-xs font-bold tracking-[0.2em] text-[#d6a954] uppercase">
            iMac performance
          </p>
          <h2 className="mt-2 text-2xl font-bold tracking-[-0.04em] text-[#fff7e7]">
            Computer overview
          </h2>
        </div>
        <button
          aria-label="Close computer overview"
          className="pointer-events-auto border border-white/15 px-3 py-2 text-xs font-bold tracking-[0.12em] text-[#c8bda9] uppercase"
          onClick={onDismiss}
          type="button"
        >
          Close · Esc
        </button>
      </div>

      {error && (
        <p className="mt-6 border border-[#e67d6f]/35 bg-[#2a1512] px-4 py-3 text-sm text-[#ffd4cc]">
          {error}
        </p>
      )}

      {snapshot ? (
        <dl className="mt-7 grid grid-cols-2 gap-x-6 gap-y-5">
          <Stat label="CPU" value={`${snapshot.cpuPercent.toFixed(1)}%`} />
          <Stat
            detail={`${snapshot.memoryUsedMiB} / ${snapshot.memoryTotalMiB} MiB`}
            label="Memory"
            value={`${snapshot.memoryPercent.toFixed(1)}%`}
          />
          <Stat
            label="Temperature"
            value={
              snapshot.temperatureC === null
                ? "—"
                : `${snapshot.temperatureC.toFixed(1)}°C`
            }
          />
          <Stat label="Load · 1 min" value={snapshot.loadOne.toFixed(2)} />
          <Stat label="Uptime" value={formatUptime(snapshot.uptimeSeconds)} />
        </dl>
      ) : (
        <p className="mt-7 border-white/10 border-t pt-5 text-sm text-[#9f9584]">
          Collecting local computer stats…
        </p>
      )}
    </aside>
  );
}
