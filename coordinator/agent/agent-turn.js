import { Agent } from "@earendil-works/pi-agent-core";

export const MAX_ANSWER_CHARACTERS = 1_000;
export const MAX_CONTEXT_BYTES = 16_384;
export const MAX_TRANSCRIPT_CHARACTERS = 4_096;

const REQUEST_ID_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$/;
const TOOL_NAME_PATTERN = /^[A-Za-z][A-Za-z0-9_-]{0,63}$/;
const MAX_TOOL_RESULT_CHARACTERS = 512;

export class AgentTurnError extends Error {
  constructor(code) {
    super(code);
    this.code = code;
  }
}

function plainObject(value) {
  return (
    value !== null &&
    typeof value === "object" &&
    !Array.isArray(value) &&
    Object.getPrototypeOf(value) === Object.prototype
  );
}

export function validateTurnRequest(value) {
  if (
    !plainObject(value) ||
    Object.keys(value).sort().join(",") !== "context,requestId,transcript" ||
    typeof value.requestId !== "string" ||
    !REQUEST_ID_PATTERN.test(value.requestId) ||
    typeof value.transcript !== "string" ||
    value.transcript.trim() !== value.transcript ||
    value.transcript.length < 1 ||
    value.transcript.length > MAX_TRANSCRIPT_CHARACTERS ||
    !plainObject(value.context)
  ) {
    throw new AgentTurnError("invalid_request");
  }

  let context;
  try {
    context = JSON.stringify(value.context);
  } catch {
    throw new AgentTurnError("invalid_request");
  }
  if (context === undefined || Buffer.byteLength(context) > MAX_CONTEXT_BYTES) {
    throw new AgentTurnError("invalid_request");
  }

  return {
    context: structuredClone(value.context),
    requestId: value.requestId,
    transcript: value.transcript,
  };
}

function validateTool(tool) {
  if (
    tool === undefined ||
    !plainObject(tool) ||
    !plainObject(tool.definition) ||
    typeof tool.definition.name !== "string" ||
    !TOOL_NAME_PATTERN.test(tool.definition.name) ||
    typeof tool.definition.label !== "string" ||
    typeof tool.definition.description !== "string" ||
    tool.definition.label.length < 1 ||
    tool.definition.description.length < 1 ||
    !tool.definition.parameters ||
    typeof tool.execute !== "function"
  ) {
    throw new AgentTurnError("invalid_tool");
  }
  return tool;
}

function answerFrom(agent) {
  const message = agent.state.messages.at(-1);
  if (message?.role === "assistant" && message.stopReason === "error") {
    throw new AgentTurnError("agent_failed");
  }
  if (
    !message ||
    message.role !== "assistant" ||
    message.stopReason !== "stop" ||
    message.content.length !== 1 ||
    message.content[0].type !== "text"
  ) {
    throw new AgentTurnError("invalid_answer");
  }

  const answer = message.content[0].text;
  if (
    answer.trim() !== answer ||
    answer.length < 1 ||
    answer.length > MAX_ANSWER_CHARACTERS
  ) {
    throw new AgentTurnError("invalid_answer");
  }
  return answer;
}

function toolCalls(agent) {
  return agent.state.messages.flatMap((message) =>
    message.role === "assistant"
      ? message.content.filter((content) => content.type === "toolCall")
      : [],
  );
}

function agentTool(tool, state, signal, onAction) {
  return {
    ...tool.definition,
    async execute(_toolCallId, arguments_) {
      if (signal?.aborted) {
        state.error = "cancelled";
        throw new AgentTurnError("cancelled");
      }
      if (state.executed) {
        state.error = "invalid_tool_request";
        throw new AgentTurnError("invalid_tool_request");
      }

      state.executed = true;
      onAction?.();
      let result;
      try {
        result = await tool.execute(structuredClone(arguments_), signal);
      } catch (error) {
        state.error = signal?.aborted ? "cancelled" : "tool_failed";
        throw error;
      }
      if (
        signal?.aborted ||
        typeof result !== "string" ||
        result.trim() !== result ||
        result.length < 1 ||
        result.length > MAX_TOOL_RESULT_CHARACTERS
      ) {
        state.error = signal?.aborted ? "cancelled" : "tool_failed";
        throw new AgentTurnError(state.error);
      }
      return {
        content: [{ type: "text", text: result }],
        details: { source: "injected" },
      };
    },
  };
}

export async function runTurn(value, options) {
  const request = validateTurnRequest(value);
  if (!options || typeof options.systemPrompt !== "string" || !options.runtime) {
    throw new AgentTurnError("agent_failed");
  }
  if (options.signal?.aborted) {
    throw new AgentTurnError("cancelled");
  }

  const tool = options.tool === undefined ? undefined : validateTool(options.tool);
  const state = { error: undefined, executed: false };
  const agent = new Agent({
    followUpMode: "one-at-a-time",
    initialState: {
      messages: [],
      model: options.runtime.model,
      systemPrompt: options.systemPrompt,
      thinkingLevel: "off",
      tools: tool ? [agentTool(tool, state, options.signal, options.onAction)] : [],
    },
    maxRetryDelayMs: 0,
    onPayload: options.onPayload,
    steeringMode: "one-at-a-time",
    streamFn: options.runtime.streamFn,
    toolExecution: "sequential",
  });

  const abort = () => agent.abort();
  options.signal?.addEventListener("abort", abort, { once: true });
  try {
    await agent.prompt(options.promptFor(request));
    if (options.signal?.aborted) {
      throw new AgentTurnError("cancelled");
    }

    const calls = toolCalls(agent);
    if (
      state.error ||
      calls.length > 1 ||
      (calls.length === 1 && (!tool || calls[0].name !== tool.definition.name)) ||
      calls.length !== Number(state.executed)
    ) {
      throw new AgentTurnError(state.error || "invalid_tool_request");
    }
    return {
      answer: answerFrom(agent),
      requestId: request.requestId,
      status: "completed",
    };
  } catch (error) {
    if (error instanceof AgentTurnError) {
      throw error;
    }
    throw new AgentTurnError(
      options.signal?.aborted ? "cancelled" : state.error || "agent_failed",
    );
  } finally {
    options.signal?.removeEventListener("abort", abort);
    agent.clearAllQueues();
  }
}

export async function readRequest(input, maximumBytes) {
  const chunks = [];
  let size = 0;
  for await (const chunk of input) {
    size += chunk.length;
    if (size > maximumBytes) {
      throw new AgentTurnError("invalid_request");
    }
    chunks.push(chunk);
  }

  const text = Buffer.concat(chunks).toString("utf8");
  if (!text.endsWith("\n") || text.slice(0, -1).includes("\n")) {
    throw new AgentTurnError("invalid_request");
  }
  try {
    return JSON.parse(text);
  } catch {
    throw new AgentTurnError("invalid_request");
  }
}
