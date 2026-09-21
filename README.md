# Mously

A tiny iPhone touchpad and media remote for macOS that runs entirely on your
local network. It has no account, cloud service, analytics, or database. The
browser and Mac communicate directly over your Wi-Fi.

## Start it

1. Install [`uv`](https://docs.astral.sh/uv/) if it is not already installed.
2. In this directory, run:

   ```sh
   uv run mously
   ```

3. The first run asks for macOS Accessibility access. Enable your terminal (or
   Codex, if launched here) in **System Settings → Privacy & Security →
   Accessibility**, then restart Mously.
4. Open the complete paired address printed by Mously, such as
   `http://192.168.1.86:8765/#token=...`, in Safari on an iPhone connected to
   the same Wi-Fi. The random pairing token changes every time Mously starts.

Keep the terminal window open while using the remote. Press `Control-C` to stop.
Use `uv run mously --port 9000` to choose another port.

## Controls

- **Absolute** mode maps phone position directly to the selected Mac screen; the outer 4% snaps to the exact screen edges.
- **Relative** mode behaves like a conventional trackpad: drag to move the pointer.
- Tap the pad or use the dedicated **Left click** button to click.
- Drag two fingers to scroll; use the dedicated button to right-click.
- **Double click** sends a native macOS double-click at the current pointer position.
- Media buttons skip back or forward five seconds, control play/pause, volume steps, and mute; a slim vertical slider beside the trackpad sets output volume directly. Hold **Zoom**, to the left of **Apps**, to temporarily replace the volume controls with a tall swipe area. Swipe up to zoom in or down to zoom out; releasing **Zoom** restores the volume control.
- **Apps** shows the Mac's currently open apps; tap one to bring it to the front.
- **Screen** changes the mapped display in Absolute mode; the largest connected display is selected by default.
- Fullscreen sends `Control-Command-F`, the standard macOS fullscreen shortcut.
- Two-finger drags always scroll or pan in any direction. Hold a third finger on the trackpad and pinch with the other two to send a native macOS magnify gesture, as with a physical trackpad in Safari, Preview, Maps, and other supported apps. In Absolute mode, magnification centers beneath the pinching pair; in Relative mode it stays beneath the existing pointer. **Pinch zoom** lets you disable it or adjust its sensitivity; the setting is saved on the phone.
- Keyboard opens a text field; **Send** types its contents into the focused Mac app.

Mously requests a short vibration for taps and buttons on browsers that implement
the web Vibration API. iPhone Safari currently does not expose that API, so iOS
shows a touch ripple on the trackpad and a confirmation pulse on control buttons.

## Security

Mously listens on the local network. Each run creates a random pairing token;
only browsers opened with the complete printed address can establish the
control WebSocket. The token is carried in the URL fragment, which is not sent
in the initial HTTP request, and is retained only for that browser tab's
session.

Traffic is not encrypted, and anyone who obtains the paired address can control
the Mac through Mously. Use it only on a network you trust, do not share the
address, and stop the process when you are finished.

## License and attribution

Mously is licensed under the GNU General Public License, version 2 or (at your
option) any later version. See [LICENSE](LICENSE).

The private macOS gesture-event serialization in `mously/macos.py` is a Python
adaptation of `tl_CGEventCreateFromGesture` from Calf Trail Software's
[Touch](https://github.com/calftrail/Touch) project, copyright 2010 Calf Trail
Software, LLC, and distributed under GPL-2.0-or-later. Hammerspoon also carries
and documents that implementation.
