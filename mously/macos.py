from __future__ import annotations

import time

import AppKit
import Quartz


KEY_CODES = {
    "enter": 36,
    "space": 49,
    "backspace": 51,
    "escape": 53,
    "left": 123,
    "right": 124,
    "down": 125,
    "up": 126,
}

MEDIA_KEYS = {
    "volume_up": 0,
    "volume_down": 1,
    "mute": 7,
    "play_pause": 16,
}


class MacController:
    def __init__(self) -> None:
        self._position = self._current_position()

    @staticmethod
    def request_accessibility() -> bool:
        if Quartz.CGPreflightPostEventAccess():
            return True
        return bool(Quartz.CGRequestPostEventAccess())

    def move(self, dx: float, dy: float) -> None:
        # A little acceleration makes crossing a TV-sized display comfortable.
        distance = (dx * dx + dy * dy) ** 0.5
        gain = 1.35 + min(distance / 24.0, 1.65)
        current = self._current_position()
        point = Quartz.CGPoint(current.x + dx * gain, current.y + dy * gain)
        event = Quartz.CGEventCreateMouseEvent(None, Quartz.kCGEventMouseMoved, point, Quartz.kCGMouseButtonLeft)
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, event)
        self._position = point

    def click(self, button: str) -> None:
        position = self._current_position()
        if button == "right":
            mouse_button = Quartz.kCGMouseButtonRight
            down_type, up_type = Quartz.kCGEventRightMouseDown, Quartz.kCGEventRightMouseUp
        else:
            mouse_button = Quartz.kCGMouseButtonLeft
            down_type, up_type = Quartz.kCGEventLeftMouseDown, Quartz.kCGEventLeftMouseUp
        for event_type in (down_type, up_type):
            event = Quartz.CGEventCreateMouseEvent(None, event_type, position, mouse_button)
            Quartz.CGEventPost(Quartz.kCGHIDEventTap, event)

    def scroll(self, dx: float, dy: float) -> None:
        # Pixel scrolling keeps two-finger movement smooth. Negation mirrors a
        # direct-manipulation touch surface (drag content in the same direction).
        event = Quartz.CGEventCreateScrollWheelEvent(
            None,
            Quartz.kCGScrollEventUnitPixel,
            2,
            int(-dy * 1.8),
            int(-dx * 1.8),
        )
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, event)

    def key(self, name: str) -> None:
        if name == "fullscreen":
            self._key_combo(3, Quartz.kCGEventFlagMaskCommand | Quartz.kCGEventFlagMaskControl)
            return
        key_code = KEY_CODES[name]
        self._key_combo(key_code)

    def text(self, value: str) -> None:
        if not value:
            return
        # Quartz accepts Unicode text on a synthetic keyboard event. Chunking
        # avoids an OS event-size edge case with long pasted strings.
        for start in range(0, len(value), 64):
            chunk = value[start : start + 64]
            for is_down in (True, False):
                event = Quartz.CGEventCreateKeyboardEvent(None, 0, is_down)
                Quartz.CGEventKeyboardSetUnicodeString(event, len(chunk), chunk)
                Quartz.CGEventPost(Quartz.kCGHIDEventTap, event)

    def media(self, name: str) -> None:
        key = MEDIA_KEYS[name]
        for is_down in (True, False):
            key_state = 0xA if is_down else 0xB
            data = (key << 16) | (key_state << 8)
            event = AppKit.NSEvent.otherEventWithType_location_modifierFlags_timestamp_windowNumber_context_subtype_data1_data2_(
                AppKit.NSEventTypeSystemDefined,
                (0, 0),
                0xA00,
                time.time(),
                0,
                None,
                8,
                data,
                -1,
            )
            Quartz.CGEventPost(Quartz.kCGHIDEventTap, event.CGEvent())

    def applications(self) -> list[dict[str, object]]:
        workspace = AppKit.NSWorkspace.sharedWorkspace()
        frontmost = workspace.frontmostApplication()
        frontmost_pid = frontmost.processIdentifier() if frontmost else None
        applications = []
        for application in workspace.runningApplications():
            if application.activationPolicy() != AppKit.NSApplicationActivationPolicyRegular:
                continue
            name = application.localizedName()
            if not name:
                continue
            pid = int(application.processIdentifier())
            applications.append({"name": str(name), "pid": pid, "active": pid == frontmost_pid})
        return sorted(applications, key=lambda app: (not app["active"], str(app["name"]).casefold()))

    @staticmethod
    def activate_application(pid: int) -> bool:
        application = AppKit.NSRunningApplication.runningApplicationWithProcessIdentifier_(pid)
        if application is None or application.activationPolicy() != AppKit.NSApplicationActivationPolicyRegular:
            return False
        return bool(application.activateWithOptions_(AppKit.NSApplicationActivateIgnoringOtherApps))

    @staticmethod
    def _key_combo(key_code: int, flags: int = 0) -> None:
        for is_down in (True, False):
            event = Quartz.CGEventCreateKeyboardEvent(None, key_code, is_down)
            if flags:
                Quartz.CGEventSetFlags(event, flags)
            Quartz.CGEventPost(Quartz.kCGHIDEventTap, event)

    @staticmethod
    def _current_position():
        return Quartz.CGEventGetLocation(Quartz.CGEventCreate(None))
