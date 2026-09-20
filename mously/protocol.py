from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class ProtocolError(ValueError):
    pass


@dataclass(frozen=True)
class Command:
    action: str
    payload: dict[str, Any]


ALLOWED_ACTIONS = {
    "move",
    "point",
    "scroll",
    "click",
    "key",
    "text",
    "media",
    "magnify",
    "list_apps",
    "activate_app",
    "list_displays",
    "select_display",
}

ALLOWED_CLICKS = {"left", "right"}
ALLOWED_KEYS = {"escape", "enter", "backspace", "space", "left", "right", "up", "down", "fullscreen"}
ALLOWED_MEDIA = {"play_pause", "volume_up", "volume_down", "mute"}
ALLOWED_MAGNIFY_PHASES = {"began", "changed", "ended", "cancelled"}


def parse_command(message: Any) -> Command:
    if not isinstance(message, dict):
        raise ProtocolError("message must be an object")

    action = message.get("action")
    if action not in ALLOWED_ACTIONS:
        raise ProtocolError("unknown action")

    payload = {key: value for key, value in message.items() if key != "action"}
    if action in {"move", "scroll"}:
        payload["dx"] = _bounded_number(payload.get("dx"), "dx")
        payload["dy"] = _bounded_number(payload.get("dy"), "dy")
    elif action == "point":
        payload["x"] = _normalized_number(payload.get("x"), "x")
        payload["y"] = _normalized_number(payload.get("y"), "y")
    elif action == "click":
        if payload.get("button") not in ALLOWED_CLICKS:
            raise ProtocolError("invalid click button")
        count = payload.get("count", 1)
        if not isinstance(count, int) or isinstance(count, bool) or count not in {1, 2}:
            raise ProtocolError("click count must be 1 or 2")
        payload["count"] = count
    elif action == "key" and payload.get("key") not in ALLOWED_KEYS:
        raise ProtocolError("invalid key")
    elif action == "media" and payload.get("key") not in ALLOWED_MEDIA:
        raise ProtocolError("invalid media key")
    elif action == "magnify":
        if payload.get("phase") not in ALLOWED_MAGNIFY_PHASES:
            raise ProtocolError("invalid magnify phase")
        payload["delta"] = _bounded_magnification(payload.get("delta"))
    elif action == "text":
        value = payload.get("text")
        if not isinstance(value, str) or len(value) > 2_000:
            raise ProtocolError("text must be a string of at most 2000 characters")
    elif action == "activate_app":
        pid = payload.get("pid")
        if not isinstance(pid, int) or isinstance(pid, bool) or not 0 < pid < 2**31:
            raise ProtocolError("pid must be a positive integer")
    elif action == "select_display":
        display_id = payload.get("display_id")
        if not isinstance(display_id, int) or isinstance(display_id, bool) or not 0 < display_id < 2**32:
            raise ProtocolError("display_id must be a positive integer")

    return Command(action, payload)


def _bounded_number(value: Any, name: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ProtocolError(f"{name} must be a number")
    return max(-500.0, min(500.0, float(value)))


def _normalized_number(value: Any, name: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ProtocolError(f"{name} must be a number")
    return max(0.0, min(1.0, float(value)))


def _bounded_magnification(value: Any) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ProtocolError("delta must be a number")
    return max(-0.5, min(0.5, float(value)))
