#!/usr/bin/env python3

import argparse
import json
import mimetypes
import os
import queue
import re
import secrets
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from agent_runtime import AgentError, NodeAgent
from context import build_answer_context, build_room_context
from hue import (
    HueAdapter,
    HueSceneError,
    HueSceneTimeout,
    HueSceneUnavailable,
)
from today import TodayAdapter, unavailable_summary
from speech import SpeechError, load_selected_speech, read_capture, read_synthesis


ACTION = "endpoint.identify"
SCENE_ACTION = "room.scene.activate"
CHANNEL_ACTION = "channel.select"
ALLOWED_ACTIONS = {ACTION, SCENE_ACTION, CHANNEL_ACTION}
CHANNELS = {"today", "music", "camera", "airplay"}
MAX_BODY_BYTES = 4096
MAX_AUDIO_BODY_BYTES = 44 + 16_000 * 2 * 15
MAX_COLLECTION_LENGTH = 512
MAX_CREATORS = 16
MAX_CREATOR_LENGTH = 256
MAX_DURATION_MS = 86_400_000
MAX_TITLE_LENGTH = 512
MAX_URI_LENGTH = 96
MAX_URL_LENGTH = 2048
MAX_REQUESTS = 128
PLAYBACK_ITEM_KEYS = {
    "artworkUrl",
    "collection",
    "creators",
    "durationMs",
    "title",
    "type",
    "uri",
}
PLAYBACK_KEYS = {"item", "positionMs", "status"}
PLAYBACK_STATUSES = {"paused", "playing", "stopped", "unavailable"}
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$")
CLIENT_ENTRY_PATTERN = re.compile(r'<script\b[^>]*\bsrc="(?P<src>/assets/[^"]+)"')
AGENT_NODE = Path("/opt/cortex-home/node/bin/node")
AGENT_CHILD = Path("/opt/cortex-home/agent/answer-child.js")
VOSK_MODEL = Path("/opt/cortex-home/models/vosk-model-small-en-us-0.15")
SPOTIFY_URI_PATTERN = re.compile(
    r"^spotify:(?P<type>track|episode):[A-Za-z0-9]{1,64}$"
)


class ApiError(Exception):
    def __init__(self, status, code, message):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


@dataclass
class PendingRequest:
    request_id: str
    action: str
    endpoint_token: str | None = None
    scene: str | None = None
    state: str = "accepted"
    error: str | None = None
    code: str | None = None
    http_status: int = HTTPStatus.OK
    finished: threading.Event = field(default_factory=threading.Event)

    def payload(self):
        payload = {
            "requestId": self.request_id,
            "action": self.action,
            "status": self.state,
        }
        if self.code:
            payload["code"] = self.code
        if self.error:
            payload["error"] = self.error
        if self.scene:
            payload["scene"] = self.scene
        return payload


@dataclass
class EndpointConnection:
    token: str = field(default_factory=lambda: secrets.token_urlsafe(24))
    events: queue.Queue = field(default_factory=queue.Queue)

    def send(self, event, data):
        self.events.put((event, data))

    def close(self):
        self.events.put(None)


@dataclass
class AgentInteraction:
    request_id: str
    endpoint_token: str
    phase: str = "transcribing"
    cancelled: threading.Event = field(default_factory=threading.Event)
    playback_timer: threading.Timer | None = None

    def payload(self):
        return {"requestId": self.request_id, "phase": self.phase}


class Coordinator:
    def __init__(
        self,
        action_timeout=10,
        scene_activator=None,
        recognizer=None,
        synthesizer=None,
        agent=None,
        playback_timeout=65,
    ):
        self.action_timeout = action_timeout
        self.scene_activator = scene_activator
        self.recognizer = recognizer
        self.synthesizer = synthesizer
        self.agent = agent
        self.playback_timeout = playback_timeout
        self.lock = threading.RLock()
        self.endpoint = None
        self.active_request_id = None
        self.requests = OrderedDict()
        self.active_interaction = None
        self.interactions = OrderedDict()
        self.playback = {
            "status": "unavailable",
            "item": None,
            "positionMs": 0,
            "observedAt": utc_timestamp(),
        }
        self.channel = {"active": "today"}
        self.today = {**unavailable_summary(), "observedAt": utc_timestamp()}
        self.hue_status = "unconfigured"
        self.lighting = {
            "status": "unavailable",
            "scenes": [],
            "activeScenes": [],
            "observedAt": utc_timestamp(),
        }

    def connect_endpoint(self):
        with self.lock:
            previous = self.endpoint
            if previous:
                self._fail_active_locked(
                    previous.token,
                    "endpoint connection was replaced",
                    HTTPStatus.SERVICE_UNAVAILABLE,
                )
                self._fail_endpoint_interaction_locked(previous.token)
                previous.close()

            self.endpoint = EndpointConnection()
            self.endpoint.send("music.playback", self.playback)
            self.endpoint.send("channel.active", self.channel)
            self.endpoint.send("today.summary", self.today)
            self.endpoint.send("room.lighting", self.lighting)
            return self.endpoint

    def disconnect_endpoint(self, token):
        with self.lock:
            if not self.endpoint or self.endpoint.token != token:
                return

            self.endpoint = None
            self._fail_active_locked(
                token,
                "endpoint disconnected",
                HTTPStatus.SERVICE_UNAVAILABLE,
            )
            self._fail_endpoint_interaction_locked(token)

    def submit(self, request_id, action, channel=None, scene=None):
        self._validate_request_id(request_id)
        if action not in ALLOWED_ACTIONS:
            raise ApiError(
                HTTPStatus.BAD_REQUEST,
                "unknown_action",
                "The action is not allowed.",
            )
        if action == CHANNEL_ACTION and channel not in CHANNELS:
            raise ApiError(
                HTTPStatus.BAD_REQUEST,
                "invalid_channel",
                "channel must be today, music, camera, or airplay.",
            )
        if action != CHANNEL_ACTION and channel is not None:
            raise ApiError(
                HTTPStatus.BAD_REQUEST,
                "invalid_action_arguments",
                "The action does not accept a channel.",
            )
        if action == SCENE_ACTION and not isinstance(scene, str):
            raise ApiError(
                HTTPStatus.BAD_REQUEST,
                "invalid_scene",
                "scene must be an available room scene.",
            )
        if action != SCENE_ACTION and scene is not None:
            raise ApiError(
                HTTPStatus.BAD_REQUEST,
                "invalid_action_arguments",
                "The action does not accept a scene.",
            )

        with self.lock:
            if action == SCENE_ACTION and (
                self.lighting["status"] != "available"
                or scene not in self.lighting["scenes"]
            ):
                raise ApiError(
                    HTTPStatus.BAD_REQUEST,
                    "invalid_scene",
                    "scene must be an available room scene.",
                )
            if request_id in self.requests:
                raise ApiError(
                    HTTPStatus.CONFLICT,
                    "duplicate_request_id",
                    "The request ID has already been used.",
                )
            if request_id in self.interactions:
                raise ApiError(
                    HTTPStatus.CONFLICT,
                    "duplicate_request_id",
                    "The request ID has already been used.",
                )
            if self.active_request_id or self.active_interaction:
                raise ApiError(
                    HTTPStatus.CONFLICT,
                    "action_busy",
                    "The room is already handling an action.",
                )
            if action == ACTION and not self.endpoint:
                raise ApiError(
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    "endpoint_unavailable",
                    "The room endpoint is not connected.",
                )

            endpoint_token = self.endpoint.token if action == ACTION else None
            pending = PendingRequest(
                request_id,
                action,
                endpoint_token,
                scene=scene,
            )
            self.requests[request_id] = pending
            self.active_request_id = request_id
            self._trim_requests_locked()
            if action == ACTION:
                self.endpoint.send(
                    "identify",
                    {"requestId": request_id, "action": ACTION},
                )
            elif self.endpoint:
                self.endpoint.send("action.status", pending.payload())

            if action == CHANNEL_ACTION:
                self._report_channel_locked(channel, force=True)
                self._finish_locked(pending, "completed", None, HTTPStatus.OK)
                return pending.http_status, pending.payload()

        if action == SCENE_ACTION:
            return self._activate_scene(pending)

        if not pending.finished.wait(self.action_timeout):
            with self.lock:
                if not pending.finished.is_set():
                    self._finish_locked(
                        pending,
                        "failed",
                        "action timed out",
                        HTTPStatus.GATEWAY_TIMEOUT,
                        code="action_timeout",
                        notify_endpoint=True,
                    )

        return pending.http_status, pending.payload()

    def interact(self, endpoint_token, request_id, audio_data, metrics=None):
        metrics = metrics if isinstance(metrics, dict) else {}
        self._validate_request_id(request_id)
        with self.lock:
            self._require_endpoint_locked(endpoint_token)
            if request_id in self.requests or request_id in self.interactions:
                raise ApiError(
                    HTTPStatus.CONFLICT,
                    "duplicate_request_id",
                    "The request ID has already been used.",
                )
            if self.active_request_id or self.active_interaction:
                raise ApiError(
                    HTTPStatus.CONFLICT,
                    "interaction_busy",
                    "The room is already handling an interaction.",
                )
            if not self.recognizer or not self.synthesizer or not self.agent:
                raise ApiError(
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    "agent_unavailable",
                    "The voice agent is unavailable.",
                )

            interaction = AgentInteraction(request_id, endpoint_token)
            self.interactions[request_id] = interaction
            self.active_interaction = interaction
            self._trim_interactions_locked()
            self._publish_interaction_locked(interaction)

        try:
            try:
                audio = read_capture(audio_data)
            except SpeechError:
                self._raise_interaction_error(
                    interaction,
                    HTTPStatus.BAD_REQUEST,
                    "invalid_audio",
                    "The captured audio is invalid.",
                )
            metrics["captureBytes"] = len(audio.data)
            metrics["captureDurationMs"] = audio.duration_ms

            self._ensure_interaction_current(interaction)
            started = time.perf_counter()
            try:
                transcript = self.recognizer.transcribe(audio)
            except SpeechError:
                self._raise_interaction_error(
                    interaction,
                    HTTPStatus.BAD_GATEWAY,
                    "transcription_failed",
                    "Speech transcription failed.",
                )
            finally:
                metrics["sttMs"] = elapsed_ms(started)
            metrics["transcriptCharacters"] = len(transcript)

            with self.lock:
                self._require_interaction_current_locked(interaction)
                context = build_answer_context(
                    self.channel.get("active"),
                    self.today,
                    self.playback,
                )
                interaction.phase = "thinking"
                self._publish_interaction_locked(interaction)

            started = time.perf_counter()
            try:
                answer = self.agent.answer(
                    request_id,
                    transcript,
                    context,
                    interaction.cancelled,
                )
            except AgentError as error:
                if error.code == "cancelled":
                    self._ensure_interaction_current(interaction)
                self._raise_interaction_error(
                    interaction,
                    (
                        HTTPStatus.GATEWAY_TIMEOUT
                        if error.code == "agent_timeout"
                        else HTTPStatus.BAD_GATEWAY
                    ),
                    error.code,
                    "The voice agent could not answer.",
                )
            finally:
                metrics["llmMs"] = elapsed_ms(started)
            metrics["answerCharacters"] = len(answer)

            self._ensure_interaction_current(interaction)
            started = time.perf_counter()
            try:
                synthesized = self.synthesizer.synthesize(answer)
                audio = read_synthesis(synthesized.data)
            except (AttributeError, SpeechError):
                self._raise_interaction_error(
                    interaction,
                    HTTPStatus.BAD_GATEWAY,
                    "synthesis_failed",
                    "Speech synthesis failed.",
                )
            finally:
                metrics["ttsMs"] = elapsed_ms(started)
            metrics["answerBytes"] = len(audio.data)
            metrics["answerDurationMs"] = audio.duration_ms

            with self.lock:
                self._require_interaction_current_locked(interaction)
                timer = threading.Timer(
                    self.playback_timeout,
                    self._expire_interaction,
                    args=(request_id, endpoint_token),
                )
                timer.daemon = True
                interaction.playback_timer = timer
                timer.start()
            return audio.data
        except ApiError:
            raise
        except Exception:
            self._raise_interaction_error(
                interaction,
                HTTPStatus.INTERNAL_SERVER_ERROR,
                "interaction_failed",
                "The voice interaction failed.",
            )

    def cancel_interaction(self, endpoint_token, request_id):
        self._validate_request_id(request_id)
        with self.lock:
            self._require_endpoint_locked(endpoint_token)
            interaction = self.interactions.get(request_id)
            if not interaction:
                if request_id in self.requests:
                    raise ApiError(
                        HTTPStatus.NOT_FOUND,
                        "unknown_interaction",
                        "No interaction matches this endpoint and request ID.",
                    )
                interaction = AgentInteraction(
                    request_id,
                    endpoint_token,
                    phase="failed",
                )
                interaction.cancelled.set()
                self.interactions[request_id] = interaction
                self._trim_interactions_locked()
                self._publish_interaction_locked(interaction)
                return interaction.payload()
            if interaction.endpoint_token != endpoint_token:
                raise ApiError(
                    HTTPStatus.NOT_FOUND,
                    "unknown_interaction",
                    "No interaction matches this endpoint and request ID.",
                )
            if interaction.phase in {"completed", "failed"}:
                return interaction.payload()
            self._finish_interaction_locked(interaction, "failed")
            return interaction.payload()

    def update_interaction(self, endpoint_token, request_id, phase):
        self._validate_request_id(request_id)
        if phase not in {"speaking", "completed", "failed"}:
            raise ApiError(
                HTTPStatus.BAD_REQUEST,
                "invalid_interaction_phase",
                "The endpoint reported an invalid interaction phase.",
            )
        with self.lock:
            self._require_endpoint_locked(endpoint_token)
            interaction = self.interactions.get(request_id)
            if not interaction or interaction.endpoint_token != endpoint_token:
                raise ApiError(
                    HTTPStatus.NOT_FOUND,
                    "unknown_interaction",
                    "No interaction matches this endpoint and request ID.",
                )
            if interaction.phase in {"completed", "failed"}:
                if phase == interaction.phase:
                    return interaction.payload()
                raise ApiError(
                    HTTPStatus.CONFLICT,
                    "interaction_finished",
                    "The interaction already reached a terminal phase.",
                )

            if phase == "speaking" and interaction.phase == "thinking":
                interaction.phase = phase
                self._publish_interaction_locked(interaction)
            elif phase in {"completed", "failed"} and (
                interaction.phase == "speaking"
                or (phase == "failed" and interaction.phase == "thinking")
            ):
                self._finish_interaction_locked(interaction, phase)
            else:
                raise ApiError(
                    HTTPStatus.CONFLICT,
                    "invalid_interaction_transition",
                    f"Cannot change {interaction.phase} to {phase}.",
                )
            return interaction.payload()

    def update(self, endpoint_token, request_id, status, error=None):
        if not endpoint_token:
            raise ApiError(
                HTTPStatus.UNAUTHORIZED,
                "missing_endpoint_token",
                "The endpoint token is required.",
            )

        with self.lock:
            if not self.endpoint or self.endpoint.token != endpoint_token:
                raise ApiError(
                    HTTPStatus.CONFLICT,
                    "stale_endpoint",
                    "The endpoint connection is no longer active.",
                )

            pending = self.requests.get(request_id)
            if not pending or pending.endpoint_token != endpoint_token:
                raise ApiError(
                    HTTPStatus.NOT_FOUND,
                    "unknown_request",
                    "No active request matches this endpoint and request ID.",
                )
            if pending.finished.is_set():
                raise ApiError(
                    HTTPStatus.CONFLICT,
                    "request_finished",
                    "The request already reached a terminal state.",
                )

            if status == "identifying" and pending.state == "accepted":
                pending.state = status
            elif status == "completed" and pending.state == "identifying":
                self._finish_locked(
                    pending,
                    status,
                    None,
                    HTTPStatus.OK,
                )
            elif status == "failed" and pending.state in {"accepted", "identifying"}:
                if not isinstance(error, str) or not error.strip():
                    raise ApiError(
                        HTTPStatus.BAD_REQUEST,
                        "missing_error",
                        "A failed endpoint status requires an error.",
                    )
                self._finish_locked(
                    pending,
                    status,
                    error.strip()[:160],
                    HTTPStatus.BAD_GATEWAY,
                )
            else:
                raise ApiError(
                    HTTPStatus.CONFLICT,
                    "invalid_transition",
                    f"Cannot change {pending.state} to {status}.",
                )

            return pending.payload()

    def is_endpoint_connected(self):
        with self.lock:
            return self.endpoint is not None

    def context(self):
        with self.lock:
            return build_room_context(
                self.channel.get("active"),
                self.today,
                self.playback,
                self.lighting,
            )

    def close(self):
        with self.lock:
            if self.active_interaction:
                self._finish_interaction_locked(
                    self.active_interaction,
                    "failed",
                )
        close_agent = getattr(self.agent, "close", None)
        if close_agent:
            close_agent()

    def set_hue_status(self, status):
        with self.lock:
            self.hue_status = status

    def set_scene_activator(self, activator):
        self.scene_activator = activator

    def report_lighting(self, lighting):
        scenes = lighting.get("scenes") if isinstance(lighting, dict) else None
        active_scenes = (
            lighting.get("activeScenes") if isinstance(lighting, dict) else None
        )
        if (
            not isinstance(lighting, dict)
            or set(lighting) != {"status", "scenes", "activeScenes"}
            or lighting["status"] not in {"available", "unavailable"}
            or not isinstance(scenes, list)
            or not all(isinstance(scene, str) and scene for scene in scenes)
            or scenes != sorted(scenes, key=str.casefold)
            or len({scene.casefold() for scene in scenes}) != len(scenes)
            or not isinstance(active_scenes, list)
            or not all(isinstance(scene, str) for scene in active_scenes)
            or active_scenes
            != [scene for scene in scenes if scene in active_scenes]
            or (
                lighting["status"] == "unavailable"
                and (scenes or active_scenes)
            )
            or (lighting["status"] == "available" and not scenes)
        ):
            raise ValueError("Invalid room lighting snapshot")

        with self.lock:
            changed = any(
                self.lighting.get(key) != lighting[key]
                for key in ("status", "scenes", "activeScenes")
            )
            if not changed:
                return self.lighting
            self.lighting = {
                "status": lighting["status"],
                "scenes": list(lighting["scenes"]),
                "activeScenes": list(lighting["activeScenes"]),
                "observedAt": utc_timestamp(),
            }
            if self.endpoint:
                self.endpoint.send("room.lighting", self.lighting)
            return self.lighting

    def report_today(self, summary):
        if not isinstance(summary, dict):
            raise ValueError("Today summary must be an object.")

        with self.lock:
            changed = any(
                self.today.get(key) != summary.get(key)
                for key in ("status", "timeZone", "current", "forecast")
            )
            if not changed:
                return self.today
            self.today = {**summary, "observedAt": utc_timestamp()}
            if self.endpoint:
                self.endpoint.send("today.summary", self.today)
            return self.today

    def health(self):
        with self.lock:
            return {
                "status": "ok",
                "endpoint": (
                    "connected" if self.endpoint is not None else "disconnected"
                ),
                "hue": self.hue_status,
            }

    def report_playback(self, observation):
        observation = validate_playback(observation)

        with self.lock:
            changed = any(
                self.playback[key] != observation[key] for key in PLAYBACK_KEYS
            )
            self.playback = {**observation, "observedAt": utc_timestamp()}
            if changed and self.endpoint:
                self.endpoint.send("music.playback", self.playback)
            return self.playback

    def _report_channel_locked(self, active, force=False):
        if active == self.channel["active"] and not force:
            return self.channel
        self.channel = {"active": active}
        if self.endpoint:
            self.endpoint.send("channel.active", self.channel)
        return self.channel

    def _fail_active_locked(self, endpoint_token, error, http_status):
        if not self.active_request_id:
            return

        pending = self.requests[self.active_request_id]
        if pending.endpoint_token == endpoint_token and not pending.finished.is_set():
            self._finish_locked(pending, "failed", error, http_status)

    def _require_endpoint_locked(self, endpoint_token):
        if not endpoint_token:
            raise ApiError(
                HTTPStatus.UNAUTHORIZED,
                "missing_endpoint_token",
                "The endpoint token is required.",
            )
        if not self.endpoint or self.endpoint.token != endpoint_token:
            raise ApiError(
                HTTPStatus.CONFLICT,
                "stale_endpoint",
                "The endpoint connection is no longer active.",
            )

    def _require_interaction_current_locked(self, interaction):
        if (
            self.active_interaction is not interaction
            or interaction.cancelled.is_set()
        ):
            raise ApiError(
                HTTPStatus.CONFLICT,
                "interaction_cancelled",
                "The interaction was cancelled.",
            )

    def _ensure_interaction_current(self, interaction):
        with self.lock:
            self._require_interaction_current_locked(interaction)

    def _raise_interaction_error(
        self,
        interaction,
        status,
        code,
        message,
    ):
        with self.lock:
            if self.active_interaction is interaction:
                self._finish_interaction_locked(interaction, "failed")
            elif interaction.cancelled.is_set():
                raise ApiError(
                    HTTPStatus.CONFLICT,
                    "interaction_cancelled",
                    "The interaction was cancelled.",
                )
        raise ApiError(status, code, message)

    def _publish_interaction_locked(self, interaction):
        if (
            self.endpoint
            and self.endpoint.token == interaction.endpoint_token
        ):
            self.endpoint.send("agent.interaction", interaction.payload())

    def _finish_interaction_locked(self, interaction, phase):
        if interaction.phase in {"completed", "failed"}:
            return
        interaction.cancelled.set()
        if interaction.playback_timer:
            interaction.playback_timer.cancel()
            interaction.playback_timer = None
        interaction.phase = phase
        if self.active_interaction is interaction:
            self.active_interaction = None
        self._publish_interaction_locked(interaction)

    def _fail_endpoint_interaction_locked(self, endpoint_token):
        interaction = self.active_interaction
        if interaction and interaction.endpoint_token == endpoint_token:
            self._finish_interaction_locked(interaction, "failed")

    def _expire_interaction(self, request_id, endpoint_token):
        with self.lock:
            interaction = self.interactions.get(request_id)
            if (
                interaction
                and interaction.endpoint_token == endpoint_token
                and self.active_interaction is interaction
            ):
                self._finish_interaction_locked(interaction, "failed")

    def _trim_interactions_locked(self):
        while len(self.interactions) > MAX_REQUESTS:
            oldest_id, oldest = next(iter(self.interactions.items()))
            if oldest.phase not in {"completed", "failed"}:
                break
            del self.interactions[oldest_id]

    def _activate_scene(self, pending):
        try:
            if self.scene_activator is None:
                raise HueSceneUnavailable
            self.scene_activator(pending.scene, self.action_timeout)
        except HueSceneUnavailable:
            result = (
                "scene_unavailable",
                f"The {pending.scene} scene is unavailable.",
                HTTPStatus.SERVICE_UNAVAILABLE,
            )
        except HueSceneTimeout:
            result = (
                "scene_timeout",
                f"The {pending.scene} scene did not report completion in time.",
                HTTPStatus.GATEWAY_TIMEOUT,
            )
        except HueSceneError:
            result = (
                "scene_failed",
                f"The Hue bridge rejected the {pending.scene} scene action.",
                HTTPStatus.BAD_GATEWAY,
            )
        else:
            with self.lock:
                self._finish_locked(pending, "completed", None, HTTPStatus.OK)
            return pending.http_status, pending.payload()

        code, error, http_status = result
        with self.lock:
            self._finish_locked(
                pending,
                "failed",
                error,
                http_status,
                code=code,
            )
        return pending.http_status, pending.payload()

    def _finish_locked(
        self,
        pending,
        state,
        error,
        http_status,
        code=None,
        notify_endpoint=False,
    ):
        pending.state = state
        pending.error = error
        pending.code = code
        pending.http_status = http_status
        if self.active_request_id == pending.request_id:
            self.active_request_id = None
        pending.finished.set()

        if pending.action in {SCENE_ACTION, CHANNEL_ACTION} and self.endpoint:
            self.endpoint.send("action.status", pending.payload())
        elif (
            notify_endpoint
            and self.endpoint
            and self.endpoint.token == pending.endpoint_token
        ):
            self.endpoint.send("result", pending.payload())

    def _trim_requests_locked(self):
        while len(self.requests) > MAX_REQUESTS:
            oldest_id, oldest = next(iter(self.requests.items()))
            if not oldest.finished.is_set():
                break
            del self.requests[oldest_id]

    @staticmethod
    def _validate_request_id(request_id):
        if not isinstance(request_id, str) or not REQUEST_ID_PATTERN.fullmatch(
            request_id
        ):
            raise ApiError(
                HTTPStatus.BAD_REQUEST,
                "invalid_request_id",
                "requestId must be 1-64 URL-safe characters.",
            )


class CortexHomeServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, server_address, coordinator, client_directory):
        self.coordinator = coordinator
        self.client_directory = Path(client_directory).resolve()
        self.client_entry = find_client_entry(self.client_directory)
        super().__init__(server_address, CortexHomeHandler)


class CortexHomeHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self):
        path = urlparse(self.path).path
        if path in {"/", "/index.html"}:
            self._serve_static("index.html")
        elif path == "/api/health":
            self._send_json(
                HTTPStatus.OK,
                self.server.coordinator.health(),
            )
        elif path == "/api/events":
            self._serve_events()
        elif path.startswith("/assets/"):
            self._serve_static(path.removeprefix("/"))
        else:
            self._send_error(
                ApiError(HTTPStatus.NOT_FOUND, "not_found", "Route not found.")
            )

    def do_POST(self):
        path = urlparse(self.path).path
        debug_metrics = None
        try:
            interaction_match = re.fullmatch(
                r"/api/agent/interactions/([^/]+)",
                path,
            )
            if interaction_match:
                request_id = interaction_match.group(1)
                self._validate_request_path(request_id)
                endpoint_token = self.headers.get("X-Endpoint-Token")
                debug_metrics = {}
                started = time.perf_counter()
                audio = self._read_audio()
                debug_metrics["uploadMs"] = elapsed_ms(started)
                result = self.server.coordinator.interact(
                    endpoint_token,
                    request_id,
                    audio,
                    debug_metrics,
                )
                try:
                    self._send_audio(result, debug_metrics)
                except (BrokenPipeError, ConnectionResetError):
                    self.server.coordinator.cancel_interaction(
                        endpoint_token,
                        request_id,
                    )
                return

            interaction_status_match = re.fullmatch(
                r"/api/agent/interactions/([^/]+)/status",
                path,
            )
            if interaction_status_match:
                request_id = interaction_status_match.group(1)
                self._validate_request_path(request_id)
                body = self._read_json({"phase"})
                payload = self.server.coordinator.update_interaction(
                    self.headers.get("X-Endpoint-Token"),
                    request_id,
                    body.get("phase"),
                )
                self._send_json(HTTPStatus.OK, payload)
                return

            if path == "/api/actions":
                body = self._read_json(
                    {"requestId", "action", "channel", "scene"}
                )
                status, payload = self.server.coordinator.submit(
                    body.get("requestId"),
                    body.get("action"),
                    body.get("channel"),
                    body.get("scene"),
                )
                self._send_json(status, payload)
                return

            if path == "/api/observations/music/playback":
                body = self._read_json(PLAYBACK_KEYS)
                payload = self.server.coordinator.report_playback(body)
                self._send_json(HTTPStatus.OK, payload)
                return

            match = re.fullmatch(r"/api/requests/([^/]+)/status", path)
            if match:
                body = self._read_json({"status", "error"})
                request_id = match.group(1)
                self._validate_request_path(request_id)
                payload = self.server.coordinator.update(
                    self.headers.get("X-Endpoint-Token"),
                    request_id,
                    body.get("status"),
                    body.get("error"),
                )
                self._send_json(HTTPStatus.OK, payload)
                return

            raise ApiError(HTTPStatus.NOT_FOUND, "not_found", "Route not found.")
        except ApiError as error:
            self._send_error(error, debug_metrics)

    def do_DELETE(self):
        path = urlparse(self.path).path
        try:
            match = re.fullmatch(r"/api/agent/interactions/([^/]+)", path)
            if not match:
                raise ApiError(
                    HTTPStatus.NOT_FOUND,
                    "not_found",
                    "Route not found.",
                )
            request_id = match.group(1)
            self._validate_request_path(request_id)
            payload = self.server.coordinator.cancel_interaction(
                self.headers.get("X-Endpoint-Token"),
                request_id,
            )
            self._send_json(HTTPStatus.OK, payload)
        except ApiError as error:
            self._send_error(error)

    def _serve_static(self, relative_path):
        file_path = (self.server.client_directory / relative_path).resolve()
        if (
            not file_path.is_relative_to(self.server.client_directory)
            or not file_path.is_file()
        ):
            self._send_error(
                ApiError(HTTPStatus.NOT_FOUND, "not_found", "Asset not found.")
            )
            return

        try:
            body = file_path.read_bytes()
        except OSError:
            self._send_error(
                ApiError(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    "client_unavailable",
                    "The endpoint client could not be loaded.",
                )
            )
            return

        content_type, _ = mimetypes.guess_type(file_path)
        self.send_response(HTTPStatus.OK)
        self.send_header(
            "Content-Type",
            content_type or "application/octet-stream",
        )
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        if file_path.name == "index.html":
            self.send_header("Cache-Control", "no-store")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; "
                "connect-src 'self' http://127.0.0.1:38019; "
                "img-src 'self' data: https:; "
                "media-src blob:; "
                "script-src 'self'; "
                "style-src 'self'",
            )
        else:
            self.send_header(
                "Cache-Control",
                "public, max-age=31536000, immutable",
            )
        self.end_headers()
        self.wfile.write(body)

    def _serve_events(self):
        endpoint = self.server.coordinator.connect_endpoint()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "keep-alive")
        self.end_headers()

        try:
            ready = {"endpointToken": endpoint.token}
            if self.server.client_entry:
                ready["clientEntry"] = self.server.client_entry
            self._write_event("ready", ready)
            while True:
                try:
                    item = endpoint.events.get(timeout=2)
                except queue.Empty:
                    self.wfile.write(b": heartbeat\n\n")
                    self.wfile.flush()
                    continue

                if item is None:
                    return

                event, data = item
                self._write_event(event, data)
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            self.close_connection = True
            self.server.coordinator.disconnect_endpoint(endpoint.token)

    def _write_event(self, event, data):
        encoded = json.dumps(data, separators=(",", ":"))
        self.wfile.write(f"event: {event}\ndata: {encoded}\n\n".encode())
        self.wfile.flush()

    def _read_json(self, allowed_keys):
        content_type = self.headers.get_content_type()
        if content_type != "application/json":
            raise ApiError(
                HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
                "invalid_content_type",
                "Content-Type must be application/json.",
            )

        content_length = self.headers.get("Content-Length")
        try:
            length = int(content_length)
        except (TypeError, ValueError):
            raise ApiError(
                HTTPStatus.LENGTH_REQUIRED,
                "missing_content_length",
                "A valid Content-Length is required.",
            )
        if length < 1 or length > MAX_BODY_BYTES:
            raise ApiError(
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                "invalid_body_size",
                f"JSON bodies must be 1-{MAX_BODY_BYTES} bytes.",
            )

        try:
            body = json.loads(self.rfile.read(length))
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise ApiError(
                HTTPStatus.BAD_REQUEST,
                "invalid_json",
                "The request body must contain valid UTF-8 JSON.",
            )

        if not isinstance(body, dict):
            raise ApiError(
                HTTPStatus.BAD_REQUEST,
                "invalid_json_shape",
                "The JSON body must be an object.",
            )

        unknown_keys = set(body) - allowed_keys
        if unknown_keys:
            raise ApiError(
                HTTPStatus.BAD_REQUEST,
                "unknown_fields",
                "The JSON body contains unknown fields.",
            )
        return body

    def _read_audio(self):
        if self.headers.get_content_type() != "audio/wav":
            raise ApiError(
                HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
                "invalid_content_type",
                "Content-Type must be audio/wav.",
            )
        content_length = self.headers.get("Content-Length")
        try:
            length = int(content_length)
        except (TypeError, ValueError):
            raise ApiError(
                HTTPStatus.LENGTH_REQUIRED,
                "missing_content_length",
                "A valid Content-Length is required.",
            )
        if length < 1 or length > MAX_AUDIO_BODY_BYTES:
            raise ApiError(
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                "invalid_body_size",
                f"Audio bodies must be 1-{MAX_AUDIO_BODY_BYTES} bytes.",
            )
        return self.rfile.read(length)

    @staticmethod
    def _validate_request_path(request_id):
        if not REQUEST_ID_PATTERN.fullmatch(request_id):
            raise ApiError(
                HTTPStatus.BAD_REQUEST,
                "invalid_request_id",
                "The request path contains an invalid request ID.",
            )

    def _send_error(self, error, debug_metrics=None):
        self._send_json(
            error.status,
            {"status": "error", "code": error.code, "error": error.message},
            debug_metrics,
        )

    def _send_json(self, status, payload, debug_metrics=None):
        body = json.dumps(payload, separators=(",", ":")).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self._send_debug_metrics(debug_metrics)
        self.end_headers()
        self.wfile.write(body)

    def _send_audio(self, body, debug_metrics=None):
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "audio/wav")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self._send_debug_metrics(debug_metrics)
        self.end_headers()
        self.wfile.write(body)

    def _send_debug_metrics(self, metrics):
        if metrics:
            self.send_header(
                "X-Cortex-Debug-Metrics",
                json.dumps(metrics, separators=(",", ":")),
            )

    def log_message(self, format, *args):
        pass


def validate_playback(observation):
    if not isinstance(observation, dict) or set(observation) != PLAYBACK_KEYS:
        raise invalid_playback()

    status = observation["status"]
    item = observation["item"]
    position_ms = observation["positionMs"]

    if (
        not isinstance(status, str)
        or status not in PLAYBACK_STATUSES
        or not bounded_integer(position_ms, 0, MAX_DURATION_MS)
    ):
        raise invalid_playback()

    if status in {"stopped", "unavailable"}:
        if item is not None or position_ms != 0:
            raise invalid_playback()
        return {"status": status, "item": None, "positionMs": 0}

    if not isinstance(item, dict) or set(item) != PLAYBACK_ITEM_KEYS:
        raise invalid_playback()

    item_type = item["type"]
    uri = item["uri"]
    uri_match = (
        SPOTIFY_URI_PATTERN.fullmatch(uri)
        if bounded_string(uri, 1, MAX_URI_LENGTH)
        else None
    )
    creators = item["creators"]
    artwork_url = item["artworkUrl"]
    parsed_artwork_url = parse_artwork_url(artwork_url)

    if (
        not isinstance(item_type, str)
        or item_type not in {"episode", "track"}
        or not uri_match
        or uri_match.group("type") != item_type
        or not bounded_string(item["title"], 1, MAX_TITLE_LENGTH)
        or not isinstance(creators, list)
        or not 1 <= len(creators) <= MAX_CREATORS
        or not all(
            bounded_string(creator, 1, MAX_CREATOR_LENGTH)
            for creator in creators
        )
        or not bounded_string(item["collection"], 1, MAX_COLLECTION_LENGTH)
        or not parsed_artwork_url
        or parsed_artwork_url.scheme != "https"
        or not parsed_artwork_url.hostname
        or parsed_artwork_url.username is not None
        or parsed_artwork_url.password is not None
        or not bounded_integer(item["durationMs"], 1, MAX_DURATION_MS)
        or position_ms > item["durationMs"]
    ):
        raise invalid_playback()

    return {
        "status": status,
        "item": {
            "uri": uri,
            "type": item_type,
            "title": item["title"],
            "creators": list(creators),
            "collection": item["collection"],
            "artworkUrl": artwork_url,
            "durationMs": item["durationMs"],
        },
        "positionMs": position_ms,
    }


def bounded_integer(value, minimum, maximum):
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and minimum <= value <= maximum
    )


def bounded_string(value, minimum, maximum):
    return (
        isinstance(value, str)
        and value.strip() == value
        and minimum <= len(value) <= maximum
    )


def parse_artwork_url(value):
    if not bounded_string(value, 1, MAX_URL_LENGTH):
        return None
    try:
        return urlparse(value)
    except ValueError:
        return None


def find_client_entry(client_directory):
    try:
        index = client_directory.joinpath("index.html").read_text()
    except (OSError, UnicodeError):
        return None

    match = CLIENT_ENTRY_PATTERN.search(index)
    return match.group("src") if match else None


def invalid_playback():
    return ApiError(
        HTTPStatus.BAD_REQUEST,
        "invalid_playback",
        "The playback observation does not match the accepted schema.",
    )


def utc_timestamp():
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def elapsed_ms(started):
    return round((time.perf_counter() - started) * 1000, 1)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument(
        "--client",
        type=Path,
        default=Path(__file__).with_name("client"),
    )
    parser.add_argument(
        "--today-cache",
        type=Path,
        default=Path("/var/cache/cortex-home/locationforecast.json"),
    )
    parser.add_argument("--action-timeout", type=float, default=10)
    parser.add_argument(
        "--hue-config",
        type=Path,
        default=Path("/etc/cortex-home/hue.json"),
    )
    return parser.parse_args()


def load_interaction_runtime():
    agent = NodeAgent(
        AGENT_NODE,
        AGENT_CHILD,
        os.environ.get("OPENROUTER_API_KEY"),
    )
    recognizer, synthesizer = load_selected_speech(VOSK_MODEL)
    return agent, recognizer, synthesizer


def main():
    args = parse_args()
    agent, recognizer, synthesizer = load_interaction_runtime()
    coordinator = Coordinator(
        action_timeout=args.action_timeout,
        agent=agent,
        recognizer=recognizer,
        synthesizer=synthesizer,
    )
    hue = HueAdapter(
        args.hue_config,
        coordinator.set_hue_status,
        coordinator.report_lighting,
    )
    coordinator.set_scene_activator(hue.activate_scene)
    today = TodayAdapter(args.today_cache, coordinator.report_today)
    server = CortexHomeServer(
        (args.host, args.port),
        coordinator,
        args.client,
    )
    hue.start()
    today.start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        coordinator.close()
        today.stop()
        hue.stop()


if __name__ == "__main__":
    main()
