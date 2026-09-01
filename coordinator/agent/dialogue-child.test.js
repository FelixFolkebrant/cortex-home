import assert from "node:assert/strict";
import test from "node:test";
import { createModels, fauxAssistantMessage, fauxProvider } from "@earendil-works/pi-ai";
import {
  answerDialogue,
  createDialogue,
  MAX_HISTORY_CHARACTERS,
  MAX_HISTORY_EXCHANGES,
} from "./dialogue-child.js";

function runtime(responses) {
  const faux = fauxProvider();
  faux.setResponses(responses);
  const models = createModels();
  models.setProvider(faux.provider);
  return { model: faux.getModel(), streamFn: models.streamSimple.bind(models) };
}

function request(index) {
  return {
    context: { activeChannel: "today", channel: { available: true, type: "today" } },
    requestId: `voice-${index}`,
    transcript: `Question ${index}?`,
  };
}

test("one dialogue keeps bounded exchanges and emits ordered text deltas", async () => {
  const deltas = [];
  const dialogue = createDialogue(
    runtime([
      fauxAssistantMessage("First answer."),
      fauxAssistantMessage("Second answer."),
      fauxAssistantMessage("Third answer."),
      fauxAssistantMessage("Fourth answer."),
      fauxAssistantMessage("Fifth answer."),
      fauxAssistantMessage("Sixth answer."),
      fauxAssistantMessage("Seventh answer."),
    ]),
    deltas.push.bind(deltas),
  );

  for (let index = 1; index <= MAX_HISTORY_EXCHANGES + 1; index += 1) {
    await answerDialogue(dialogue, request(index));
  }

  assert.equal(deltas.join(""), "First answer.Second answer.Third answer.Fourth answer.Fifth answer.Sixth answer.Seventh answer.");
  assert.equal(dialogue.state.messages.length, MAX_HISTORY_EXCHANGES * 2);
  assert.equal(dialogue.state.messages[0].role, "user");
});

test("one dialogue removes complete exchanges above the character bound", async () => {
  const dialogue = createDialogue(
    runtime([
      fauxAssistantMessage("First answer."),
      fauxAssistantMessage("Second answer."),
      fauxAssistantMessage("Third answer."),
    ]),
  );

  for (let index = 1; index <= 3; index += 1) {
    await answerDialogue(dialogue, {
      ...request(index),
      transcript: `Question ${index}: ${"x".repeat(3_000)}`,
    });
  }

  const characters = dialogue.state.messages.reduce(
    (total, message) => total + message.content.reduce(
      (messageTotal, content) => messageTotal + (content.type === "text" ? content.text.length : 0),
      0,
    ),
    0,
  );
  assert.ok(characters <= MAX_HISTORY_CHARACTERS);
  assert.equal(dialogue.state.messages.length % 2, 0);
  assert.match(dialogue.state.messages[0].content[0].text, /Question 3:/);
});
