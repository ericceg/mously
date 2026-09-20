import pytest

from mously import macos


def test_largest_external_display_is_preferred():
    displays = [
        {"display_id": 1, "width": 1512, "height": 982, "builtin": True},
        {"display_id": 2, "width": 1920, "height": 1080, "builtin": False},
    ]
    assert macos.MacController._choose_largest_display(displays) == 2


def test_absolute_point_maps_to_selected_display(monkeypatch):
    posted = []
    bounds = macos.Quartz.CGRectMake(100, -900, 1920, 1080)

    controller = macos.MacController.__new__(macos.MacController)
    controller._selected_display_id = 7
    controller._position = None
    monkeypatch.setattr(controller, "displays", lambda: [{"display_id": 7, "selected": True}])
    monkeypatch.setattr(macos.Quartz, "CGDisplayBounds", lambda _display_id: bounds)
    monkeypatch.setattr(
        macos.Quartz,
        "CGEventCreateMouseEvent",
        lambda _source, _type, point, _button: point,
    )
    monkeypatch.setattr(macos.Quartz, "CGEventPost", lambda _tap, event: posted.append(event))

    controller.point(0.0, 1.0)
    assert posted[-1].x == 100
    assert posted[-1].y == 179

    controller.point(1.0, 0.0)
    assert posted[-1].x == 2019
    assert posted[-1].y == -900


def test_double_click_posts_two_clicks_with_native_click_states(monkeypatch):
    events = []
    posted = []

    monkeypatch.setattr(macos.MacController, "_current_position", staticmethod(lambda: (10, 20)))

    def create_event(_source, event_type, _position, button):
        event = {"type": event_type, "button": button}
        events.append(event)
        return event

    monkeypatch.setattr(macos.Quartz, "CGEventCreateMouseEvent", create_event)
    monkeypatch.setattr(
        macos.Quartz,
        "CGEventSetIntegerValueField",
        lambda event, _field, value: event.update(click_state=value),
    )
    monkeypatch.setattr(macos.Quartz, "CGEventPost", lambda _tap, event: posted.append(event.copy()))
    monkeypatch.setattr(macos.time, "sleep", lambda _seconds: None)

    controller = macos.MacController.__new__(macos.MacController)
    controller.click("left", 2)

    assert len(events) == 4
    assert [event["click_state"] for event in posted] == [1, 1, 2, 2]
    assert all(event["button"] == macos.Quartz.kCGMouseButtonLeft for event in posted)


def test_scroll_carries_fractional_pixels_between_events(monkeypatch):
    events = []
    controller = macos.MacController.__new__(macos.MacController)
    monkeypatch.setattr(
        macos.Quartz,
        "CGEventCreateScrollWheelEvent",
        lambda _source, _unit, _axes, vertical, horizontal: (vertical, horizontal),
    )
    monkeypatch.setattr(macos.Quartz, "CGEventPost", lambda _tap, event: events.append(event))

    controller.scroll(0.3, 0.3)
    controller.scroll(0.3, 0.3)

    assert events == [(0, 0), (1, 1)]
    assert controller._scroll_remainder_x == pytest.approx(0.08)
    assert controller._scroll_remainder_y == pytest.approx(0.08)


def test_magnify_posts_native_gesture_to_session(monkeypatch):
    event = object()
    posted = []
    controller = macos.MacController.__new__(macos.MacController)
    monkeypatch.setattr(macos, "_create_magnify_event", lambda delta, phase: (event, delta, phase))
    monkeypatch.setattr(macos.Quartz, "CGEventPost", lambda tap, value: posted.append((tap, value)))

    controller.magnify(0.08, "changed")

    assert posted == [(macos.Quartz.kCGSessionEventTap, (event, 0.08, "changed"))]


def test_volume_reads_and_sets_master_output(monkeypatch):
    writes = []
    controller = macos.MacController.__new__(macos.MacController)
    monkeypatch.setattr(macos, "_default_output_device", lambda: 42)
    monkeypatch.setattr(macos, "_get_audio_float", lambda device, selector, scope, element: 0.375)
    monkeypatch.setattr(macos, "_set_audio_uint32", lambda *args: True)
    monkeypatch.setattr(
        macos,
        "_set_audio_float",
        lambda device, selector, scope, element, value: writes.append(
            (device, selector, scope, element, value)
        ) or True,
    )

    assert controller.volume() == pytest.approx(0.375)
    controller.set_volume(0.8)
    assert writes == [(42, "volm", "outp", 0, 0.8)]


def test_synthetic_magnify_event_decodes_as_native_appkit_gesture():
    event = macos._create_magnify_event(0.08, "changed")
    native = macos.AppKit.NSEvent.eventWithCGEvent_(event)

    assert native.type() == macos.AppKit.NSEventTypeMagnify
    assert native.phase() == macos.AppKit.NSEventPhaseChanged
    assert native.magnification() == pytest.approx(0.08)
