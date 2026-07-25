import { cva } from "class-variance-authority";
import { useEffect, useRef, useState } from "react";
import { cn } from "./classes";

const stateCopy = {
  connecting: ["Finding the room.", "Connecting to the coordinator."],
  ready: ["Room endpoint ready.", "Waiting for an identify request."],
  identifying: ["Here I am.", "Playing the room signal."],
  completed: ["Identified.", "The room confirmed the request."],
  failed: ["Couldn’t identify.", "The request failed."],
  disconnected: ["Coordinator offline.", "Reconnecting automatically."],
};

const screen = cva(
  "min-h-screen overflow-hidden bg-[#11100d] text-[#f8f0dc] transition-[background] duration-300",
  {
    variants: {
      state: {
        connecting: "bg-[radial-gradient(circle_at_50%_35%,#24221c_0,transparent_38%)]",
        ready: "bg-[radial-gradient(circle_at_50%_35%,#343026_0,transparent_38%)]",
        identifying:
          "bg-[#17110b] bg-[radial-gradient(circle_at_50%_42%,#6f451d_0,transparent_44%)]",
        completed: "bg-[radial-gradient(circle_at_50%_35%,#24382a_0,transparent_40%)]",
        failed: "bg-[radial-gradient(circle_at_50%_35%,#3c211e_0,transparent_40%)]",
        disconnected:
          "bg-[radial-gradient(circle_at_50%_35%,#24221c_0,transparent_38%)]",
      },
    },
  },
);

const signal = cva(
  "mx-auto mt-16 aspect-square w-[clamp(8rem,14vw,14rem)] rounded-full border-2 transition-[border-color,box-shadow,transform] duration-300 motion-reduce:animate-none",
  {
    variants: {
      state: {
        connecting: "border-[#706a5d] shadow-[0_0_0_1rem_rgb(112_106_93_/_8%)]",
        ready:
          "border-[#c89542] shadow-[0_0_0_1rem_rgb(200_149_66_/_8%),0_0_5rem_rgb(200_149_66_/_18%)]",
        identifying:
          "animate-identify border-[#ffd27d] shadow-[0_0_0_2rem_rgb(255_210_125_/_16%),0_0_9rem_rgb(255_177_63_/_70%)]",
        completed:
          "scale-[1.08] border-[#92d6a1] shadow-[0_0_0_1.5rem_rgb(146_214_161_/_14%),0_0_7rem_rgb(146_214_161_/_45%)]",
        failed:
          "border-[#e67d6f] shadow-[0_0_0_1.5rem_rgb(230_125_111_/_12%),0_0_6rem_rgb(230_125_111_/_38%)]",
        disconnected: "border-[#706a5d] shadow-[0_0_0_1rem_rgb(112_106_93_/_8%)]",
      },
    },
  },
);

function Signal({ state, className }) {
  return <div aria-hidden="true" className={cn(signal({ state }), className)} />;
}

async function playIdentifySound() {
  const context = new AudioContext();
  if (context.state === "suspended") {
    await context.resume();
  }
  if (context.state !== "running") {
    await context.close();
    throw new Error("Browser audio did not start.");
  }

  const startedAt = context.currentTime + 0.05;
  for (const [frequency, offset] of [
    [440, 0],
    [660, 0.42],
    [880, 0.84],
  ]) {
    const oscillator = new OscillatorNode(context, { frequency });
    const gain = new GainNode(context, { gain: 0.14 });
    oscillator.connect(gain).connect(context.destination);
    oscillator.start(startedAt + offset);
    oscillator.stop(startedAt + offset + 0.28);
  }

  await new Promise((resolve) => setTimeout(resolve, 1500));
  await context.close();
}

export function App() {
  const [view, setView] = useState({
    state: "connecting",
    message: stateCopy.connecting[1],
  });
  const endpointToken = useRef(null);
  const activeRequestId = useRef(null);
  const actionGeneration = useRef(0);

  useEffect(() => {
    function showState(state, message) {
      setView({ state, message: message || stateCopy[state][1] });
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
      showState("identifying");

      try {
        await postStatus(requestId, "identifying");
        await playIdentifySound();

        if (generation !== actionGeneration.current) {
          return;
        }

        await postStatus(requestId, "completed");
        activeRequestId.current = null;
        showState("completed");
        setTimeout(() => {
          if (generation === actionGeneration.current) {
            showState("ready");
          }
        }, 2500);
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
        showState("failed", message);
      }
    }

    const events = new EventSource("/api/events");

    events.addEventListener("ready", (event) => {
      const message = JSON.parse(event.data);
      endpointToken.current = message.endpointToken;
      actionGeneration.current += 1;
      activeRequestId.current = null;
      showState("ready");
    });

    events.addEventListener("identify", (event) => {
      const message = JSON.parse(event.data);
      if (!activeRequestId.current) {
        identify(message.requestId);
      }
    });

    events.addEventListener("result", (event) => {
      const message = JSON.parse(event.data);
      if (
        message.requestId === activeRequestId.current &&
        message.status === "failed"
      ) {
        actionGeneration.current += 1;
        activeRequestId.current = null;
        showState("failed", message.error);
      }
    });

    events.onerror = () => {
      endpointToken.current = null;
      actionGeneration.current += 1;
      activeRequestId.current = null;
      showState("disconnected");
    };

    return () => events.close();
  }, []);

  return (
    <div className={screen({ state: view.state })}>
      <main
        aria-live="polite"
        className="grid min-h-screen place-content-center px-[8vw] text-center"
      >
        <p className="mb-6 text-[clamp(1rem,1.8vw,1.75rem)] tracking-[0.28em] text-[#c8bda4] uppercase">
          Cortex Home
        </p>
        <h1 className="mx-auto max-w-[14ch] text-[clamp(5rem,10vw,11rem)] leading-[0.9] font-bold tracking-[-0.07em]">
          {stateCopy[view.state][0]}
        </h1>
        <p className="mt-8 min-h-[1.5em] text-[clamp(1.25rem,2.2vw,2.25rem)] text-[#d5c9af]">
          {view.message}
        </p>
        <Signal state={view.state} />
      </main>
    </div>
  );
}
