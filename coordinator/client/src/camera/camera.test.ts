import assert from "node:assert/strict";
import test from "node:test";
import {
  CAMERA_CONSTRAINTS,
  cameraFailureStatus,
  startCameraCapture,
} from "./camera.ts";

class FakeTrack {
  constructor(kind = "video") {
    this.kind = kind;
    this.readyState = "live";
    this.stopCount = 0;
    this.listeners = new Set();
  }

  addEventListener(event, listener) {
    if (event === "ended") {
      this.listeners.add(listener);
    }
  }

  removeEventListener(event, listener) {
    if (event === "ended") {
      this.listeners.delete(listener);
    }
  }

  end() {
    this.readyState = "ended";
    for (const listener of [...this.listeners]) {
      listener();
    }
  }

  stop() {
    this.stopCount += 1;
    this.readyState = "ended";
  }
}

class FakePage {
  constructor() {
    this.listeners = new Set();
  }

  addEventListener(event, listener) {
    if (event === "pagehide") {
      this.listeners.add(listener);
    }
  }

  removeEventListener(event, listener) {
    if (event === "pagehide") {
      this.listeners.delete(listener);
    }
  }

  hide() {
    for (const listener of [...this.listeners]) {
      listener();
    }
  }
}

function fakeStream(...tracks) {
  return {
    getTracks: () => tracks,
    getVideoTracks: () => tracks.filter((track) => track.kind === "video"),
  };
}

function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, reject, resolve };
}

async function settleCapture() {
  await Promise.resolve();
  await Promise.resolve();
}

test("capture requests video only, attaches it, and stops every owned track", async () => {
  const videoTrack = new FakeTrack();
  const unexpectedAudioTrack = new FakeTrack("audio");
  const stream = fakeStream(videoTrack, unexpectedAudioTrack);
  const video = { srcObject: null };
  const statuses = [];
  const requests = [];

  const cleanup = startCameraCapture({
    mediaDevices: {
      getUserMedia: (constraints) => {
        requests.push(constraints);
        return Promise.resolve(stream);
      },
    },
    onStatus: (status) => statuses.push(status),
    pageTarget: new FakePage(),
    secureContext: true,
    video,
  });
  await settleCapture();

  assert.deepEqual(requests, [CAMERA_CONSTRAINTS]);
  assert.deepEqual(CAMERA_CONSTRAINTS, { audio: false, video: true });
  assert.equal(video.srcObject, stream);
  assert.deepEqual(statuses, ["live"]);

  cleanup();

  assert.equal(video.srcObject, null);
  assert.equal(videoTrack.stopCount, 1);
  assert.equal(unexpectedAudioTrack.stopCount, 1);
});

test("a stale capture result stops itself without attaching", async () => {
  const capture = deferred();
  const track = new FakeTrack();
  const stream = fakeStream(track);
  const video = { srcObject: null };
  const statuses = [];

  const cleanup = startCameraCapture({
    mediaDevices: { getUserMedia: () => capture.promise },
    onStatus: (status) => statuses.push(status),
    secureContext: true,
    video,
  });
  cleanup();
  capture.resolve(stream);
  await settleCapture();

  assert.equal(video.srcObject, null);
  assert.equal(track.stopCount, 1);
  assert.deepEqual(statuses, []);
});

test("an ended track releases the whole stream and requires reentry", async () => {
  const firstTrack = new FakeTrack();
  const secondTrack = new FakeTrack();
  const stream = fakeStream(firstTrack, secondTrack);
  const video = { srcObject: null };
  const statuses = [];

  const cleanup = startCameraCapture({
    mediaDevices: { getUserMedia: () => Promise.resolve(stream) },
    onStatus: (status) => statuses.push(status),
    secureContext: true,
    video,
  });
  await settleCapture();
  firstTrack.end();

  assert.equal(video.srcObject, null);
  assert.equal(firstTrack.stopCount, 1);
  assert.equal(secondTrack.stopCount, 1);
  assert.deepEqual(statuses, ["live", "ended"]);

  cleanup();
  assert.equal(firstTrack.stopCount, 1);
  assert.equal(secondTrack.stopCount, 1);
});

test("leaving and reentering makes one fresh capture attempt", async () => {
  const streams = [fakeStream(new FakeTrack()), fakeStream(new FakeTrack())];
  const video = { srcObject: null };
  let requestCount = 0;
  const mediaDevices = {
    getUserMedia: () => Promise.resolve(streams[requestCount++]),
  };

  const leaveFirst = startCameraCapture({
    mediaDevices,
    onStatus: () => {},
    secureContext: true,
    video,
  });
  await settleCapture();
  leaveFirst();

  const leaveSecond = startCameraCapture({
    mediaDevices,
    onStatus: () => {},
    secureContext: true,
    video,
  });
  await settleCapture();

  assert.equal(requestCount, 2);
  assert.equal(streams[0].getTracks()[0].stopCount, 1);
  assert.equal(video.srcObject, streams[1]);

  leaveSecond();
});

test("reload cleanup stops every track", async () => {
  const tracks = [new FakeTrack(), new FakeTrack()];
  const page = new FakePage();
  const video = { srcObject: null };

  startCameraCapture({
    mediaDevices: { getUserMedia: () => Promise.resolve(fakeStream(...tracks)) },
    onStatus: () => {},
    pageTarget: page,
    secureContext: true,
    video,
  });
  await settleCapture();
  page.hide();

  assert.equal(video.srcObject, null);
  assert.deepEqual(
    tracks.map((track) => track.stopCount),
    [1, 1],
  );
});

test("unsupported, policy, permission, and device failures stay distinct", async () => {
  const video = { srcObject: null };
  const statuses = [];
  const report = (status) => statuses.push(status);

  startCameraCapture({
    mediaDevices: undefined,
    onStatus: report,
    secureContext: true,
    video,
  });
  startCameraCapture({
    mediaDevices: { getUserMedia: () => Promise.resolve() },
    onStatus: report,
    secureContext: false,
    video,
  });
  startCameraCapture({
    mediaDevices: {
      getUserMedia: () => Promise.reject({ name: "NotAllowedError" }),
    },
    onStatus: report,
    secureContext: true,
    video,
  });
  startCameraCapture({
    mediaDevices: {
      getUserMedia: () => Promise.reject({ name: "NotFoundError" }),
    },
    onStatus: report,
    secureContext: true,
    video,
  });
  await settleCapture();

  assert.deepEqual(statuses, ["unsupported", "blocked", "denied", "unavailable"]);
  assert.equal(cameraFailureStatus({ name: "SecurityError" }), "blocked");
});
