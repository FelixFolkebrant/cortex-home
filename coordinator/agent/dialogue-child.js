import { pathToFileURL } from "node:url";
import { createModels } from "@earendil-works/pi-ai";
import { openrouterProvider } from "@earendil-works/pi-ai/providers/openrouter";
import { Agent } from "@earendil-works/pi-agent-core";
import {
  AgentTurnError,
  MAX_ANSWER_CHARACTERS,
  validateTurnRequest,
} from "./agent-turn.js";
import { OPENROUTER_MODEL, lockProviderPayload } from "./answer-child.js";

export const MAX_HISTORY_CHARACTERS = 6_000;
export const MAX_HISTORY_EXCHANGES = 6;

const SYSTEM_PROMPT = [
  "You are the Cortex Home voice assistant.",
  "Answer the user's current spoken question concisely in plain text.",
  "Do not use markup, tools, or mention private system details.",
].join(" ");

function promptFor(request) {
  return [
    "Current room context JSON:",
    JSON.stringify(request.context),
    "",
    "Current spoken question:",
    request.transcript,
  ].join("\n");
}

function textSize(message) {
  return message.content?.reduce(
    (total, content) => total + (content.type === "text" ? content.text.length : 0),
    0,
  ) || 0;
}

export function trimHistory(agent) {
  while (
    agent.state.messages.length > MAX_HISTORY_EXCHANGES * 2 ||
    agent.state.messages.reduce((total, message) => total + textSize(message), 0) >
      MAX_HISTORY_CHARACTERS
  ) {
    agent.state.messages.splice(0, 2);
  }
}

function answerFrom(agent) {
  const message = agent.state.messages.at(-1);
  const answer = message?.role === "assistant" && message.content?.length === 1 &&
    message.content[0].type === "text" && message.stopReason === "stop"
    ? message.content[0].text
    : null;
  if (!answer || answer.trim() !== answer || answer.length > MAX_ANSWER_CHARACTERS) {
    throw new AgentTurnError("invalid_answer");
  }
  return answer;
}

export function createDialogue(runtime = productionRuntime(), emit = () => {}) {
  const agent = new Agent({
    followUpMode: "one-at-a-time",
    initialState: {
      messages: [],
      model: runtime.model,
      systemPrompt: SYSTEM_PROMPT,
      thinkingLevel: "off",
      tools: [],
    },
    maxRetryDelayMs: 0,
    onPayload: lockProviderPayload,
    steeringMode: "one-at-a-time",
    streamFn: runtime.streamFn,
  });
  agent.subscribe((event) => {
    if (event.type === "message_update" && event.assistantMessageEvent.type === "text_delta") {
      emit(event.assistantMessageEvent.delta);
    }
  });
  return agent;
}

export async function answerDialogue(agent, value) {
  const request = validateTurnRequest(value);
  trimHistory(agent);
  await agent.prompt(promptFor(request));
  const answer = answerFrom(agent);
  trimHistory(agent);
  return answer;
}

function productionRuntime() {
  const models = createModels();
  models.setProvider(openrouterProvider());
  return { model: OPENROUTER_MODEL, streamFn: models.streamSimple.bind(models) };
}

async function main() {
  let currentRequestId = null;
  const dialogue = createDialogue(undefined, (delta) => {
    process.stdout.write(`${JSON.stringify({ delta, requestId: currentRequestId, type: "delta" })}\n`);
  });
  for await (const line of process.stdin) {
    let request;
    try {
      request = JSON.parse(line);
      currentRequestId = request.requestId;
      const answer = await answerDialogue(dialogue, request);
      process.stdout.write(`${JSON.stringify({ answer, requestId: currentRequestId, status: "completed", type: "completed" })}\n`);
    } catch (error) {
      process.stdout.write(`${JSON.stringify({ code: error instanceof AgentTurnError ? error.code : "agent_failed", requestId: currentRequestId, type: "failed" })}\n`);
    }
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  await main();
}
