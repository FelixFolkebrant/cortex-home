import assert from "node:assert/strict";
import test from "node:test";
import {
  createModels,
  fauxAssistantMessage,
  fauxProvider,
  fauxThinking,
  fauxToolCall,
} from "@earendil-works/pi-ai";
import {
  AgentRequestError,
  answerRequest,
  lockProviderPayload,
  MAX_ANSWER_CHARACTERS,
  MAX_OUTPUT_TOKENS,
  validateRequest,
} from "./answer-child.js";

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
        ["agent_failed", "invalid_answer"].includes(error.code),
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
