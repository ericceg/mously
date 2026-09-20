# Mously

A tiny, local-only iPhone absolute touchpad and media remote for macOS. It has no account,
cloud service, analytics, or database. The browser and Mac communicate directly
over your Wi-Fi.

## Start it

1. Install [`uv`](https://docs.astral.sh/uv/) if it is not already installed.
2. In this directory, run:

   ```sh
   uv run mously
   ```

3. The first run asks for macOS Accessibility access. Enable your terminal (or
   Codex, if launched here) in **System Settings → Privacy & Security →
   Accessibility**, then restart Mously.
4. Open the printed address, such as `http://192.168.1.86:8765`, in Safari on an
   iPhone connected to the same Wi-Fi.

Keep the terminal window open while using the remote. Press `Control-C` to stop.
Use `uv run mously --port 9000` to choose another port.

## Controls

- Touch or drag one finger to place the pointer at the matching position on the selected Mac screen; tap to left-click.
- Drag two fingers to scroll; use the dedicated button to right-click.
- **Double click** sends a native macOS double-click at the current pointer position.
- Media buttons control play/pause, volume, and mute.
- **Apps** shows the Mac's currently open apps; tap one to bring it to the front.
- The screen name in the header changes the mapped display; the largest connected display is selected by default.
- Fullscreen sends `Control-Command-F`, the standard macOS fullscreen shortcut.
- Keyboard opens a text field; **Send** types its contents into the focused Mac app.

Mously requests a short vibration for taps and buttons on browsers that implement
the web Vibration API. iPhone Safari currently does not expose that API, so iOS
shows a touch ripple on the trackpad and a confirmation pulse on control buttons.

Mously listens on the local network without authentication. Use it only on a
network you trust, and stop the process when you are finished.
