from mously import macos


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
