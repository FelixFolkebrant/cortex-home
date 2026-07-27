export function AirPlayChannel() {
  return (
    <main
      aria-label="AirPlay screen mirror"
      className="relative z-10 grid min-h-screen place-content-center px-[8vw] text-center"
    >
      <p className="text-[clamp(0.8rem,1vw,1.1rem)] font-bold tracking-[0.28em] text-[#d6a954] uppercase">
        Cortex Home / AirPlay
      </p>
      <h1 className="mx-auto mt-7 max-w-[12ch] text-[clamp(4rem,8vw,9rem)] leading-[0.9] font-bold tracking-[-0.07em] text-[#fff7e7]">
        Ready to mirror.
      </h1>
      <p className="mx-auto mt-8 max-w-[38rem] text-[clamp(1.2rem,2vw,2rem)] leading-relaxed text-[#c9bda6]">
        Open Screen Mirroring on the iPhone and choose Cortex AirPlay.
      </p>
      <p className="mt-5 text-sm font-bold tracking-[0.18em] text-[#efc66f] uppercase">
        No code required
      </p>
      <p className="mt-12 text-sm tracking-[0.12em] text-[#837968]">
        Ctrl + Alt + 4 stops AirPlay and returns to Today
      </p>
    </main>
  );
}
