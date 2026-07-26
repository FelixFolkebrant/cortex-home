# GH-014 Plan: Qualify Deliberate Local Speech

# What

- Establish one deliberate `Ctrl`+`Alt`+`Space` hold-to-capture boundary for
  the USB-connected Anker PowerConf S330.
- Provision Chromium's exact configured coordinator origin for secure-context
  media access and grant only microphone capture without a wildcard policy.
- Capture one bounded mono PCM utterance in Chromium and keep audio on the LAN.
- Qualify English Vosk against a quantized `whisper.cpp` model and Piper against
  Pocket TTS on the ThinkPad using the real microphone and Sonos playback path.
- Add one small recognizer contract and one small synthesizer contract, then pin
  the measured winner for each role.
- Record capture start, transcription, synthesis, first-audio, playback-stop,
  CPU, and memory results before the agent depends on them.

## Out Of Scope

- Pi Agent Core, `pi-ai`, OpenRouter, prompts, model credentials, or language
  reasoning.
- A spoken answer, conversation state, tool call, Hue action, or agent
  interaction overlay.
- Wake words, click-to-toggle recording, voice activity detection, background
  recording, streaming speech-to-speech, or barge-in.
- Camera activation, video permission, frames, or the Camera channel.
- Persisting recordings, transcripts, synthesized audio, or qualification
  utterance contents in the repository or application logs.
- A general speech service, backend plugin registry, or runtime backend
  switching UI.

## Deferred

- GH-016 integrates the selected speech backends with the supervised Pi process
  and visible request-ID interaction lifecycle.
- GH-017 rebases this issue's exact-origin Chromium security policy and adds
  only the corresponding video-capture allowlist for the Camera mirror.
- Exact spoken-prefix reconciliation and mid-speech interruption remain
  deferred until a first complete spoken turn is qualified.

## Acceptance Criteria

- [ ] `Ctrl`+`Alt`+`Space` is the only new accepted capture shortcut; capture
  exists only while held, repeat and extra modifiers are ignored, and key
  release or cancellation closes every audio track.
- [ ] Chromium treats only the configured coordinator origin as the accepted
  secure-context exception and grants only that origin microphone access
  without an interactive kiosk prompt.
- [ ] Reprovisioning renders the policy from the configured origin rather than
  storing a deployment hostname in the repository.
- [ ] Browser capture produces one bounded, documented mono PCM shape accepted
  by either recognizer and never sends audio outside the LAN.
- [ ] English Vosk and one pinned quantized `whisper.cpp` model are measured on
  the ThinkPad with the same representative room utterances.
- [ ] Piper and Pocket TTS are measured with the same short answer texts through
  the real endpoint and Sonos route.
- [ ] One recognizer and one synthesizer are selected from recorded accuracy,
  listening quality, latency, CPU, memory, install size, and operational
  evidence.
- [ ] The selected roles implement two small contracts that do not expose
  engine-specific objects to coordinator behavior.
- [ ] Capture start, transcription, synthesis, first-audio, and playback-stop
  measurements are bounded to at most 60 seconds each and their useful summary
  is recorded without utterance content or host identity.
- [ ] Cancelling capture or playback releases browser media tracks, stops local
  audio promptly, and ignores stale results by qualification request ID.
- [ ] Missing microphone, denied permission, invalid PCM, backend failure, and
  endpoint playback failure each fail explicitly.
- [ ] Provisioning checks, backend tests, frontend checks, Python suites,
  production build, production audit, and whitespace checks pass.

# Tasks

## 1. Provision The Exact Media Origin

- Render a Chromium managed-policy file during iMac provisioning from the
  validated coordinator URL.
- Add the exact origin to the secure-context override and audio-capture
  allowlist without enabling video, wildcard origins, or all-media approval.
- Verify the installed policy and unattended capture behavior after a kiosk
  restart.

## 2. Capture One Press-Bounded Utterance

- Add fixed shortcut classification and a small browser capture boundary that
  requests mono audio only after the key press.
- Convert the bounded input to the documented PCM shape and close every track
  on release, cancellation, error, or cleanup.
- Keep qualification lifecycle keyed by one request ID so stale capture or
  playback results can be rejected.

## 3. Qualify Recognition Backends

- Pin reviewed Vosk and quantized `whisper.cpp` candidates plus the exact English
  models used for comparison.
- Run the same bounded room utterances through both on the ThinkPad and record
  accuracy, latency, CPU, memory, storage, and failure behavior.
- Select one backend and expose it through the minimal recognizer contract.

## 4. Qualify Synthesis Backends

- Pin reviewed Piper and Pocket TTS candidates plus the exact English voices
  used for comparison.
- Run the same short answer texts through both, play their bounded output over
  the existing endpoint/Sonos path, and measure generation and stop latency.
- Select one backend and expose it through the minimal synthesizer contract.

## 5. Record Reproducible Qualification

- Add repository-owned verification commands for the selected installation,
  models, capture shape, backend contracts, resource limits, and failure cases.
- Create `docs/wip/GH-014.md` with exact provisioning and qualification commands,
  summarized evidence, problems, caveats, and reviewer-owned listening checks.

# Heatmap

Reference: `../project/HEATMAP.md`.

## Hot

### H1 - Make Hold State The Capture Authority

- Decision: Microphone tracks exist only between the accepted shortcut press
  and release for one request ID.
- Proposed approach: Reject repeats and extra modifiers, start capture on the
  initial keydown, and stop all tracks on keyup, blur, cancellation, error, or
  component cleanup.
- Why: A deliberate microphone must not become a toggle or survive loss of
  keyboard focus.
- Alternatives: Click-to-toggle; fixed recording duration; voice activity
  detection; background stream reuse.
- Review focus: Every terminal and interrupted path releases the device and
  rejects stale results.

### H2 - Scope Unattended Permission To One Origin

- Decision: Establish one generated exact-origin Chromium media policy shared
  with the later Camera issue.
- Proposed approach: Use the configured coordinator origin for the supported
  secure-context override and audio-capture allowlist; do not grant video in
  this issue.
- Why: `getUserMedia` requires a secure context and a kiosk cannot rely on an
  interactive prompt, but broad sensor permission would violate the privacy
  boundary.
- Alternatives: Deploy TLS now; global auto-approval flag; wildcard managed
  policy; endpoint capture daemon.
- Review focus: Exact origin matching, idempotent provisioning, no committed
  deployment identity, and no video grant.

### H3 - Select Backends From Real Evidence

- Decision: Pin the measured recognizer and synthesizer winners rather than
  making every candidate a permanent runtime option.
- Proposed approach: Compare candidates behind the same bounded inputs and
  output path, record the decision, and retain only two small selected-role
  contracts in product code.
- Why: Runtime configurability before qualification would preserve complexity
  instead of preserving a useful replacement seam.
- Alternatives: Choose from documentation; ship every engine; make backend
  selection a user setting.
- Review focus: Fair inputs, actual-room listening judgment, resource evidence,
  and a contract small enough to replace later.
