import pytest

from mously.protocol import ProtocolError, parse_command


def test_move_is_parsed_and_bounded():
    command = parse_command({"action": "move", "dx": 999, "dy": -2})
    assert command.action == "move"
    assert command.payload == {"dx": 500.0, "dy": -2.0}


@pytest.mark.parametrize(
    "message",
    [
        {},
        {"action": "launch_missiles"},
        {"action": "click", "button": "middle"},
        {"action": "click", "button": "left", "count": 3},
        {"action": "click", "button": "left", "count": True},
        {"action": "move", "dx": "fast", "dy": 1},
        {"action": "point", "x": "left", "y": 0.5},
        {"action": "text", "text": "x" * 2001},
    ],
)
def test_invalid_commands_are_rejected(message):
    with pytest.raises(ProtocolError):
        parse_command(message)


def test_expected_controls_are_allowed():
    assert parse_command({"action": "media", "key": "play_pause"}).payload["key"] == "play_pause"
    assert parse_command({"action": "key", "key": "fullscreen"}).payload["key"] == "fullscreen"
    assert parse_command({"action": "list_apps"}).action == "list_apps"
    assert parse_command({"action": "list_displays"}).action == "list_displays"
    assert parse_command({"action": "activate_app", "pid": 123}).payload["pid"] == 123


def test_click_count_defaults_to_one_and_allows_double_click():
    assert parse_command({"action": "click", "button": "left"}).payload["count"] == 1
    assert parse_command({"action": "click", "button": "left", "count": 2}).payload["count"] == 2


def test_absolute_points_are_clamped_to_the_screen():
    command = parse_command({"action": "point", "x": -0.2, "y": 1.2})
    assert command.payload == {"x": 0.0, "y": 1.0}


@pytest.mark.parametrize("pid", [None, True, 0, -1, 2**31, "123"])
def test_invalid_application_pids_are_rejected(pid):
    with pytest.raises(ProtocolError):
        parse_command({"action": "activate_app", "pid": pid})


@pytest.mark.parametrize("display_id", [None, True, 0, -1, 2**32, "2"])
def test_invalid_display_ids_are_rejected(display_id):
    with pytest.raises(ProtocolError):
        parse_command({"action": "select_display", "display_id": display_id})
