import { useEffect, useState } from "react";
import { requestEndpointControl } from "../../shared/endpoint-control";

function AirPlayLogo({ className = "" }) {
  return (
    <svg aria-hidden="true" className={className} fill="none" viewBox="0 0 52 52">
      <rect
        height="30"
        rx="4"
        stroke="currentColor"
        strokeWidth="3"
        width="42"
        x="5"
        y="6"
      />
      <path d="M26 27 14 45h24L26 27Z" fill="currentColor" />
    </svg>
  );
}

function AppleTvLogo() {
  return (
    <span aria-label="Apple TV" className="inline-flex items-center gap-1.5" role="img">
      <svg
        aria-hidden="true"
        className="h-[1.15em] w-[1em]"
        fill="currentColor"
        viewBox="0 0 26 30"
      >
        <path d="M17.1 8.2c-1.7-.1-3.1 1-4 1-1 0-2.3-1-3.8-1-2 0-3.8 1.2-4.8 3-2.1 3.6-.5 9 1.5 11.9 1 1.4 2.1 2.9 3.7 2.8 1.5-.1 2.1-.9 3.9-.9 1.7 0 2.3.9 3.8.9 1.6 0 2.6-1.4 3.6-2.8 1.1-1.6 1.6-3.2 1.6-3.3-3.4-1.4-4-6.1-.7-8-1-1.4-2.8-2.5-4.8-2.6ZM16 5.9c.8-1 1.4-2.5 1.2-3.9-1.3.1-2.9.9-3.8 2-.8.9-1.5 2.4-1.3 3.8 1.5.1 3-.7 3.9-1.9Z" />
      </svg>
      <span className="font-semibold tracking-[-0.05em]">tv</span>
    </span>
  );
}

export function isAirPlayToggleShortcut(event) {
  return (
    event.key === "Enter" &&
    !event.altKey &&
    !event.ctrlKey &&
    !event.metaKey &&
    !event.shiftKey &&
    !event.repeat
  );
}

export async function requestAirPlay(path, fetcher = fetch, wait) {
  let response;

  try {
    response = await requestEndpointControl(
      path,
      { method: path === "/status" ? "GET" : "POST" },
      fetcher,
      wait,
    );
  } catch {
    throw new Error("AirPlay control is unavailable.");
  }

  const result = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(result.error || "AirPlay is unavailable.");
  }
  if (!["off", "on"].includes(result.state)) {
    throw new Error("AirPlay returned an invalid state.");
  }

  return result.state;
}

export function AirPlayStatus({ state, error }) {
  if (state === "starting") {
    return (
      <span
        aria-label="Starting AirPlay"
        className="h-10 w-10 animate-spin rounded-full border-4 border-white/25 border-t-white"
        role="status"
      />
    );
  }
  if (state === "on") {
    return (
      <p className="text-2xl font-medium tracking-[-0.025em] text-white/80">
        Select{" "}
        <span className="mx-1 inline-flex items-center gap-2 text-white">
          <AppleTvLogo />
          <span>Skärmen</span>
        </span>{" "}
        to cast screen
      </p>
    );
  }
  if (error) {
    return <p className="text-lg font-medium text-[#ff6961]">{error}</p>;
  }

  return null;
}

export function AirPlayChannel() {
  const [state, setState] = useState("off");
  const [error, setError] = useState(null);

  useEffect(() => {
    let current = true;

    requestAirPlay("/status")
      .then((nextState) => {
        if (current) {
          setState(nextState);
        }
      })
      .catch((requestError) => {
        if (current) {
          setError(requestError.message);
        }
      });

    return () => {
      current = false;
    };
  }, []);

  const enabled = state === "on" || state === "starting";
  const working = state === "starting" || state === "stopping";

  async function toggle() {
    const nextEnabled = !enabled;
    setError(null);
    setState(nextEnabled ? "starting" : "stopping");

    try {
      setState(await requestAirPlay(nextEnabled ? "/on" : "/off"));
    } catch (requestError) {
      setState(nextEnabled ? "off" : "on");
      setError(requestError.message);
    }
  }

  useEffect(() => {
    function onKeyDown(event) {
      if (
        working ||
        !isAirPlayToggleShortcut(event) ||
        event.target?.closest?.('[role="switch"]')
      ) {
        return;
      }

      event.preventDefault();
      toggle();
    }

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  });

  return (
    <main
      aria-label="AirPlay screen mirror"
      className="relative z-10 grid min-h-screen place-content-center bg-[#080808] px-[8vw] text-center text-white"
    >
      <div className="flex items-center justify-center gap-5">
        <AirPlayLogo className="h-14 w-14" />
        <h1 className="text-6xl font-semibold tracking-[-0.055em]">AirPlay</h1>
      </div>

      <button
        aria-checked={enabled}
        aria-keyshortcuts="Enter"
        aria-label="AirPlay receiver"
        className={`relative mx-auto mt-16 h-[4.25rem] w-[7.5rem] rounded-full p-1.5 shadow-inner transition-colors duration-300 focus-visible:outline-4 focus-visible:outline-offset-8 focus-visible:outline-white ${
          enabled ? "bg-[#30d158]" : "bg-[#3a3a3c]"
        }`}
        disabled={working}
        onClick={toggle}
        role="switch"
        type="button"
      >
        <span
          aria-hidden="true"
          className={`block aspect-square h-full rounded-full bg-white shadow-[0_2px_8px_rgb(0_0_0_/_45%)] transition-transform duration-300 ${
            enabled ? "translate-x-[3.25rem]" : "translate-x-0"
          }`}
        />
      </button>

      <div aria-live="polite" className="mt-14 grid min-h-20 place-content-center">
        <AirPlayStatus error={error} state={state} />
      </div>
    </main>
  );
}
