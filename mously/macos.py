from __future__ import annotations

import ctypes
import struct
import time

import AppKit
import Foundation
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

MAGNIFY_PHASES = {
    "began": 1,
    "changed": 2,
    "ended": 4,
    "cancelled": 8,
}


class _DigitizerEventData(ctypes.Structure):
    _fields_ = [
        ("size", ctypes.c_uint32),
        ("type", ctypes.c_uint32),
        ("timestamp", ctypes.c_uint64),
        ("options", ctypes.c_uint32),
        ("position_x", ctypes.c_int32),
        ("position_y", ctypes.c_int32),
        ("position_z", ctypes.c_int32),
        ("transducer_index", ctypes.c_uint32),
        ("transducer_type", ctypes.c_uint32),
        ("identity", ctypes.c_uint32),
        ("event_mask", ctypes.c_uint32),
        ("child_event_mask", ctypes.c_uint32),
        ("button_mask", ctypes.c_uint32),
        ("tip_pressure", ctypes.c_int32),
        ("barrel_pressure", ctypes.c_int32),
        ("twist", ctypes.c_int32),
        ("orientation_type", ctypes.c_uint32),
        ("orientation_quality", ctypes.c_int32),
        ("orientation_density", ctypes.c_int32),
        ("orientation_irregularity", ctypes.c_int32),
        ("orientation_major_radius", ctypes.c_int32),
        ("orientation_minor_radius", ctypes.c_int32),
    ]


class _VendorDefinedEventData(ctypes.Structure):
    _fields_ = [
        ("size", ctypes.c_uint32),
        ("type", ctypes.c_uint32),
        ("timestamp", ctypes.c_uint64),
        ("options", ctypes.c_uint32),
        ("usage_page", ctypes.c_uint16),
        ("usage", ctypes.c_uint16),
        ("version", ctypes.c_uint32),
        ("length", ctypes.c_uint32),
    ]


class _SystemQueueElement(ctypes.Structure):
    _fields_ = [
        ("timestamp", ctypes.c_uint64),
        ("device_id", ctypes.c_uint64),
        ("options", ctypes.c_uint32),
        ("event_count", ctypes.c_uint32),
    ]


def _structure_bytes(value: ctypes.Structure) -> bytes:
    return ctypes.string_at(ctypes.addressof(value), ctypes.sizeof(value))


def _gesture_uint32(field: int, value: int) -> bytes:
    return struct.pack(">HBBI", 1, 0x40, field, value)


def _gesture_float32(field: int, value: float) -> bytes:
    return struct.pack(">HBBf", 1, 0xC0, field, value)


def _create_magnify_event(delta: float, phase: str):
    """Create the private CGEvent envelope macOS uses for trackpad gestures.

    AppKit exposes magnify events publicly but Core Graphics has no public
    system-wide constructor for them. This serialization format is private,
    so it is intentionally isolated here and covered by an AppKit decode test.
    Its envelope follows calftrail/Touch's ``tl_CGEventCreateFromGesture``
    format, also used by Hammerspoon's gesture event implementation.
    """
    prototype = Quartz.CGEventCreate(None)
    Quartz.CGEventSetType(prototype, AppKit.NSEventTypeGesture)
    Quartz.CGEventSetFlags(prototype, 0x100)  # NX_NONCOALSESCEDMASK
    timestamp = time.monotonic_ns()
    Quartz.CGEventSetTimestamp(prototype, timestamp)

    # The serialized prototype ends in a 24-byte empty field array. Replace
    # it with an IOHID hand collection, the multitouch vendor token, and the
    # fields describing this magnification delta.
    blob = bytes(Quartz.CGEventCreateData(None, prototype))[:-24]
    queue = _SystemQueueElement(timestamp=timestamp, options=2, event_count=2)
    digitizer = _DigitizerEventData(
        size=ctypes.sizeof(_DigitizerEventData),
        type=11,
        timestamp=timestamp,
        options=2,
        transducer_type=0x23,
        orientation_type=2,
    )
    vendor_payload_size = 40
    vendor = _VendorDefinedEventData(
        size=ctypes.sizeof(_VendorDefinedEventData) + vendor_payload_size,
        type=1,
        timestamp=timestamp,
        usage_page=0xFF00,
        usage=0x1777,
        version=1,
        length=vendor_payload_size,
    )
    payload_size = (
        ctypes.sizeof(queue)
        + ctypes.sizeof(digitizer)
        + ctypes.sizeof(vendor)
        + vendor_payload_size
    )
    blob += struct.pack(">HBB", payload_size, 0x10, 0x6D)
    blob += _structure_bytes(queue) + _structure_bytes(digitizer) + _structure_bytes(vendor)
    blob += bytes(vendor_payload_size)
    blob += _gesture_uint32(0x6E, 0x08)  # magnify subtype
    blob += _gesture_uint32(0x6F, 0)
    blob += _gesture_uint32(0x70, 0)
    blob += _gesture_uint32(0x84, MAGNIFY_PHASES[phase])
    blob += _gesture_uint32(0x85, 0)
    blob += _gesture_float32(0x71, delta)
    blob += _gesture_float32(0x8B, 0)
    blob += _gesture_float32(0x8C, 0)

    data = Foundation.NSData.dataWithBytes_length_(blob, len(blob))
    return Quartz.CGEventCreateFromData(None, data)


class MacController:
    def __init__(self) -> None:
        self._position = self._current_position()
        self._selected_display_id = self._default_display_id()

    @staticmethod
    def request_accessibility() -> bool:
        if Quartz.CGPreflightPostEventAccess():
            return True
        return bool(Quartz.CGRequestPostEventAccess())

    def move(self, dx: float, dy: float) -> None:
        # A little acceleration makes crossing a TV-sized display comfortable.
        distance = (dx * dx + dy * dy) ** 0.5
        gain = 1.8 + min(distance / 20.0, 3)
        current = self._current_position()
        point = Quartz.CGPoint(current.x + dx * gain, current.y + dy * gain)
        event = Quartz.CGEventCreateMouseEvent(None, Quartz.kCGEventMouseMoved, point, Quartz.kCGMouseButtonLeft)
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, event)
        self._position = point

    def point(self, x: float, y: float) -> None:
        displays = self.displays()
        selected = next((display for display in displays if display["selected"]), None)
        if selected is None:
            self._selected_display_id = self._default_display_id()
        bounds = Quartz.CGDisplayBounds(self._selected_display_id)
        point = Quartz.CGPoint(
            bounds.origin.x + x * max(bounds.size.width - 1, 0),
            bounds.origin.y + y * max(bounds.size.height - 1, 0),
        )
        event = Quartz.CGEventCreateMouseEvent(None, Quartz.kCGEventMouseMoved, point, Quartz.kCGMouseButtonLeft)
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, event)
        self._position = point

    def click(self, button: str, count: int = 1) -> None:
        position = self._current_position()
        if button == "right":
            mouse_button = Quartz.kCGMouseButtonRight
            down_type, up_type = Quartz.kCGEventRightMouseDown, Quartz.kCGEventRightMouseUp
        else:
            mouse_button = Quartz.kCGMouseButtonLeft
            down_type, up_type = Quartz.kCGEventLeftMouseDown, Quartz.kCGEventLeftMouseUp
        for click_number in range(1, count + 1):
            for event_type in (down_type, up_type):
                event = Quartz.CGEventCreateMouseEvent(None, event_type, position, mouse_button)
                Quartz.CGEventSetIntegerValueField(event, Quartz.kCGMouseEventClickState, click_number)
                Quartz.CGEventPost(Quartz.kCGHIDEventTap, event)
            if click_number < count:
                time.sleep(0.06)

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

    def magnify(self, delta: float, phase: str) -> None:
        event = _create_magnify_event(delta, phase)
        if event is not None:
            # Session-level posting matches the route used by real trackpad
            # gestures and targets the view beneath the pointer at Began.
            Quartz.CGEventPost(Quartz.kCGSessionEventTap, event)

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

    def displays(self) -> list[dict[str, object]]:
        result, display_ids, _count = Quartz.CGGetActiveDisplayList(16, None, None)
        if result != Quartz.kCGErrorSuccess:
            return []
        names = {
            int(screen.deviceDescription()["NSScreenNumber"]): str(screen.localizedName())
            for screen in AppKit.NSScreen.screens()
        }
        displays = []
        for display_id in display_ids:
            display_id = int(display_id)
            bounds = Quartz.CGDisplayBounds(display_id)
            displays.append(
                {
                    "display_id": display_id,
                    "name": names.get(display_id, f"Display {display_id}"),
                    "width": int(bounds.size.width),
                    "height": int(bounds.size.height),
                    "selected": display_id == self._selected_display_id,
                    "builtin": bool(Quartz.CGDisplayIsBuiltin(display_id)),
                }
            )
        if displays and not any(display["selected"] for display in displays):
            self._selected_display_id = self._choose_largest_display(displays)
            for display in displays:
                display["selected"] = display["display_id"] == self._selected_display_id
        return sorted(displays, key=lambda display: (not display["selected"], display["builtin"], display["name"]))

    def select_display(self, display_id: int) -> bool:
        available_ids = {display["display_id"] for display in self.displays()}
        if display_id not in available_ids:
            return False
        self._selected_display_id = display_id
        return True

    @staticmethod
    def activate_application(pid: int) -> bool:
        application = AppKit.NSRunningApplication.runningApplicationWithProcessIdentifier_(pid)
        if application is None or application.activationPolicy() != AppKit.NSApplicationActivationPolicyRegular:
            return False
        return bool(application.activateWithOptions_(AppKit.NSApplicationActivateIgnoringOtherApps))

    def _default_display_id(self) -> int:
        result, display_ids, _count = Quartz.CGGetActiveDisplayList(16, None, None)
        if result != Quartz.kCGErrorSuccess or not display_ids:
            return int(Quartz.CGMainDisplayID())
        candidates = []
        for display_id in display_ids:
            bounds = Quartz.CGDisplayBounds(display_id)
            candidates.append(
                {
                    "display_id": int(display_id),
                    "width": int(bounds.size.width),
                    "height": int(bounds.size.height),
                    "builtin": bool(Quartz.CGDisplayIsBuiltin(display_id)),
                }
            )
        return self._choose_largest_display(candidates)

    @staticmethod
    def _choose_largest_display(displays: list[dict[str, object]]) -> int:
        display = max(
            displays,
            key=lambda item: (int(item["width"]) * int(item["height"]), not bool(item["builtin"])),
        )
        return int(display["display_id"])

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
