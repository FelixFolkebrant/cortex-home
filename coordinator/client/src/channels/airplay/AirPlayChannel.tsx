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

export function AirPlayChannel() {
  return (
    <main
      aria-label="AirPlay screen mirror"
      className="relative z-10 grid min-h-screen place-content-center bg-[#080808] px-[8vw] text-center text-white"
    >
      <div className="flex items-center justify-center gap-5">
        <AirPlayLogo className="h-14 w-14" />
        <h1 className="text-6xl font-semibold tracking-[-0.055em]">AirPlay</h1>
      </div>

      <p className="mt-14 text-2xl font-medium tracking-[-0.025em] text-white/80">
        Select{" "}
        <span className="mx-1 inline-flex items-center gap-2 text-white">
          <AppleTvLogo />
          <span>Skärmen</span>
        </span>{" "}
        to cast screen
      </p>
    </main>
  );
}
