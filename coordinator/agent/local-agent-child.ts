import { pathToFileURL } from "node:url";
import { createModels } from "@earendil-works/pi-ai";
import { openrouterProvider } from "@earendil-works/pi-ai/providers/openrouter";
import {
  AgentTurnError,
  readRequest,
  runTurn,
  validateTurnRequest,
} from "./agent-turn.ts";
import {
  MAX_INPUT_BYTES,
  MAX_OUTPUT_TOKENS,
  OPENROUTER_MODEL,
  lockProviderPayload,
} from "./answer-child.ts";
import { developmentTool } from "./development-tool.ts";

const LOCAL_CONTEXT = Object.freeze({
  home: Object.freeze({
    music: Object.freeze({ available: false, type: "music" }),
    today: Object.freeze({ available: false, type: "today" }),
  }),
});
const SYSTEM_PROMPT = [
  "You are running one local Cortex Home development voice interaction.",
  "The supplied context is only a local development marker, not observed room data.",
  "Answer the user's current question in one or two concise plain-text sentences.",
  "You may call the one development tool only when the user explicitly asks to test it.",
  "Its result is simulated; never claim that a room, device, or production state was contacted or observed.",
  "Do not ask a follow-up question and do not use markup.",
].join(" ");

function localRequest(value) {
  const request = validateTurnRequest(value);
  if (JSON.stringify(request.context) !== JSON.stringify(LOCAL_CONTEXT)) {
    throw new AgentTurnError("invalid_request");
  }
  return request;
}

function promptFor(request) {
  return ["Current spoken question:", request.transcript].join("\n");
}

function runtime() {
  const models = createModels();
  models.setProvider(openrouterProvider());
  return {
    model: OPENROUTER_MODEL,
    streamFn: models.streamSimple.bind(models),
  };
}

async function main() {
  const controller = new AbortController();
  const abort = () => controller.abort();
  process.once("SIGINT", abort);
  process.once("SIGTERM", abort);

  let result;
  let exitCode = 0;
  try {
    const request = localRequest(await readRequest(process.stdin, MAX_INPUT_BYTES));
    result = await runTurn(request, {
      onAction: () => process.stderr.write('{"phase":"acting"}\n'),
      onPayload: (payload) => {
        const locked = lockProviderPayload(payload, true);
        locked.max_tokens = MAX_OUTPUT_TOKENS;
        return locked;
      },
      promptFor,
      runtime: runtime(),
      signal: controller.signal,
      systemPrompt: SYSTEM_PROMPT,
      tool: developmentTool,
    });
  } catch (error) {
    result = {
      code: error instanceof AgentTurnError ? error.code : "agent_failed",
      status: "failed",
    };
    exitCode = 1;
  }
  process.stdout.write(`${JSON.stringify(result)}\n`, () => {
    process.exitCode = exitCode;
  });
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  await main();
}
