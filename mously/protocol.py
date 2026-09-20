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
    "scroll",
    "click",
    "key",
    "text",
    "media",
    "list_apps",
    "activate_app",
}

ALLOWED_CLICKS = {"left", "right"}
ALLOWED_KEYS = {"escape", "enter", "backspace", "space", "left", "right", "up", "down", "fullscreen"}
ALLOWED_MEDIA = {"play_pause", "volume_up", "volume_down", "mute"}


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
    elif action == "click" and payload.get("button") not in ALLOWED_CLICKS:
        raise ProtocolError("invalid click button")
    elif action == "key" and payload.get("key") not in ALLOWED_KEYS:
        raise ProtocolError("invalid key")
    elif action == "media" and payload.get("key") not in ALLOWED_MEDIA:
        raise ProtocolError("invalid media key")
    elif action == "text":
        value = payload.get("text")
        if not isinstance(value, str) or len(value) > 2_000:
            raise ProtocolError("text must be a string of at most 2000 characters")
    elif action == "activate_app":
        pid = payload.get("pid")
        if not isinstance(pid, int) or isinstance(pid, bool) or not 0 < pid < 2**31:
            raise ProtocolError("pid must be a positive integer")

    return Command(action, payload)


def _bounded_number(value: Any, name: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ProtocolError(f"{name} must be a number")
    return max(-500.0, min(500.0, float(value)))
