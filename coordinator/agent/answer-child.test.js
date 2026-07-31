import assert from "node:assert/strict";
import test from "node:test";
import {
  createModels,
  fauxAssistantMessage,
  fauxProvider,
  fauxThinking,
  fauxToolCall,
} from "@earendil-works/pi-ai";
import { Type } from "typebox";
import {
  AgentRequestError,
  answerRequest,
  lockProviderPayload,
  MAX_ANSWER_CHARACTERS,
  MAX_OUTPUT_TOKENS,
  validateRequest,
} from "./answer-child.js";
import { AgentTurnError, runTurn } from "./agent-turn.js";

const request = {
  context: {
    activeChannel: "today",
    channel: {
      available: true,
      current: { condition: "Clear", temperatureC: 21 },
      type: "today",
    },
  },
  requestId: "voice-test-1",
  transcript: "Do I need a jacket?",
};

function runtime(responses) {
  const faux = fauxProvider();
  faux.setResponses(responses);
  const models = createModels();
  models.setProvider(faux.provider);
  return {
    faux,
    model: faux.getModel(),
    streamFn: models.streamSimple.bind(models),
  };
}

function developmentTool(execute = async () => "Simulated result.") {
  return {
    definition: {
      description: "Returns a simulated local development result.",
      label: "Development test",
      name: "development_test",
      parameters: Type.Object({}, { additionalProperties: false }),
    },
    execute,
  };
}

function localTurn(responses, tool, options = {}) {
  return runTurn(request, {
    onPayload: lockProviderPayload,
    promptFor: () => "Local test prompt",
    runtime: runtime(responses),
    systemPrompt: "Local test system prompt",
    tool,
    ...options,
  });
}

test("one faux Pi turn returns one bounded answer without tools", async () => {
  const fake = runtime([fauxAssistantMessage("A light jacket should be enough.")]);

  const result = await answerRequest(request, { runtime: fake });

  assert.deepEqual(result, {
    answer: "A light jacket should be enough.",
    requestId: "voice-test-1",
    status: "completed",
  });
  assert.equal(fake.faux.state.callCount, 1);
});

test("one injected tool continues in the same Pi turn", async () => {
  const calls = [];
  const phases = [];
  const result = await localTurn(
    [
      fauxAssistantMessage(fauxToolCall("development_test", {}), {
        stopReason: "toolUse",
      }),
      fauxAssistantMessage("The simulated development tool completed."),
    ],
    developmentTool(async (arguments_) => {
      calls.push(arguments_);
      return "Simulated result: no room hardware was contacted or observed.";
    }),
    { onAction: () => phases.push("acting") },
  );

  assert.equal(result.answer, "The simulated development tool completed.");
  assert.deepEqual(calls, [{}]);
  assert.deepEqual(phases, ["acting"]);
});

test("unknown, malformed, and repeated tool calls do not execute", async () => {
  const cases = [
    [fauxToolCall("unknown_tool", {})],
    [fauxToolCall("development_test", { unexpected: true })],
    [fauxToolCall("development_test", {}), fauxToolCall("development_test", {})],
  ];

  for (const calls of cases) {
    let executions = 0;
    await assert.rejects(
      localTurn(
        [
          fauxAssistantMessage(calls, { stopReason: "toolUse" }),
          fauxAssistantMessage("This must not become an answer."),
        ],
        developmentTool(async () => {
          executions += 1;
          return "Simulated result.";
        }),
      ),
      (error) =>
        error instanceof AgentTurnError && error.code === "invalid_tool_request",
    );
    assert.equal(executions, calls[0].name === "development_test" && calls.length === 2 ? 1 : 0);
  }
});

test("cancelled and failed injected tools cannot produce a late answer", async () => {
  const controller = new AbortController();
  let release;
  const pending = new Promise((resolve) => {
    release = resolve;
  });
  const result = localTurn(
    [
      fauxAssistantMessage(fauxToolCall("development_test", {}), {
        stopReason: "toolUse",
      }),
      fauxAssistantMessage("This must be ignored."),
    ],
    developmentTool(async () => pending),
    { signal: controller.signal },
  );
  controller.abort();
  release("Simulated result.");

  await assert.rejects(
    result,
    (error) => error instanceof AgentTurnError && error.code === "cancelled",
  );

  await assert.rejects(
    localTurn(
      [
        fauxAssistantMessage(fauxToolCall("development_test", {}), {
          stopReason: "toolUse",
        }),
      ],
      developmentTool(async () => {
        throw new Error("private failure");
      }),
    ),
    (error) => error instanceof AgentTurnError && error.code === "tool_failed",
  );
});

test("the child request is exact, bounded, and channel scoped", () => {
  assert.deepEqual(validateRequest(request), request);
  for (const invalid of [
    {},
    { ...request, extra: true },
    { ...request, requestId: "../bad" },
    { ...request, transcript: "" },
    { ...request, transcript: " padded " },
    { ...request, transcript: "x".repeat(4_097) },
    { ...request, context: [] },
    { ...request, context: { activeChannel: "camera" } },
    { ...request, context: { ...request.context, lighting: {} } },
  ]) {
    assert.throws(
      () => validateRequest(invalid),
      (error) => error instanceof AgentRequestError && error.code === "invalid_request",
    );
  }
});

test("provider payload always carries the privacy and output controls", () => {
  const payload = lockProviderPayload({
    messages: [{ content: "private", role: "user" }],
    model: "unexpected",
    models: ["fallback"],
    reasoning: { effort: "high" },
    tool_choice: "auto",
    tools: [{ name: "unsafe" }],
  });

  assert.equal(payload.model, "google/gemini-3.5-flash-lite");
  assert.equal(payload.max_tokens, MAX_OUTPUT_TOKENS);
  assert.equal(payload.store, false);
  assert.deepEqual(payload.provider, {
    allow_fallbacks: false,
    data_collection: "deny",
    only: ["google-vertex/global"],
    require_parameters: true,
    zdr: true,
  });
  assert.equal("models" in payload, false);
  assert.equal("reasoning" in payload, false);
  assert.equal("tools" in payload, false);
  assert.equal("tool_choice" in payload, false);
});

test("thinking, tool calls, truncation, and unsafe answer shapes fail", async () => {
  const cases = [
    fauxAssistantMessage([fauxThinking("private"), { type: "text", text: "Answer" }]),
    fauxAssistantMessage(fauxToolCall("unsafe", {}), { stopReason: "toolUse" }),
    fauxAssistantMessage("partial", { stopReason: "length" }),
    fauxAssistantMessage(` ${"x".repeat(MAX_ANSWER_CHARACTERS)}`),
  ];

  for (const response of cases) {
    await assert.rejects(
      answerRequest(request, { runtime: runtime([response]) }),
      (error) =>
        error instanceof AgentRequestError &&
        ["agent_failed", "invalid_answer", "invalid_tool_request"].includes(
          error.code,
        ),
    );
  }
});

test("provider errors become content-free agent failures", async () => {
  await assert.rejects(
    answerRequest(request, {
      runtime: runtime([
        fauxAssistantMessage([], {
          errorMessage: "private provider detail",
          stopReason: "error",
        }),
      ]),
    }),
    (error) => error instanceof AgentRequestError && error.code === "agent_failed",
  );
});

test("an aborted turn cannot return its late answer", async () => {
  const controller = new AbortController();
  const fake = runtime([fauxAssistantMessage("This must be ignored.")]);
  controller.abort();

  await assert.rejects(
    answerRequest(request, { runtime: fake, signal: controller.signal }),
    (error) => error instanceof AgentRequestError && error.code === "cancelled",
  );
});
