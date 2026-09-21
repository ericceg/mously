# Mously

**Use your iPhone as a trackpad and media remote for your Mac.**

Mously runs entirely on your local network. There is no iPhone app to install,
no account, no cloud service, and no analytics. Just open the paired address in
Safari and control your Mac from your phone.

## Why I Built This

I wanted a simple solution to control my Mac from my iPhone. 
It should be fast, easy to set up, be able to do all the essential things and 
should not require an account or send anything through someone else's server.
Mously turns your phone already in your hand into
a trackpad, keyboard, app switcher, and media remote.

## Installation

Mously requires macOS, Python 3.11+, and
[`uv`](https://docs.astral.sh/uv/getting-started/installation/).

```bash
uv tool install git+https://github.com/ericceg/mously.git
mously
```

On first launch, allow your terminal to control the Mac under **System Settings
→ Privacy & Security → Accessibility**, then restart Mously.

Open the complete paired address printed in the terminal on an iPhone connected
to the same Wi-Fi. Keep Mously running while you use the remote; press
`Control-C` to stop it.

To use a different port:

```bash
mously --port 9000
```

## What It Does

- Move the mouse cursor with your finger
- Tap, double-click, right-click, scroll, and use native pinch-to-zoom gestures
- Control playback, volume, mute, and fullscreen mode
- Swipe to zoom in and out with the dedicated hold-to-zoom control
- Bring any open Mac app to the front
- Type text into the focused Mac app


## Security

Each run creates a new random pairing token. Only a browser opened with the
complete address printed by Mously can connect.

**Important security note:**
Traffic is not encrypted, and anyone with that address can control your Mac.
Use Mously only on a network you trust, do not share the address, and stop it
when you are finished.

## Development

Run directly from the repository:

```bash
uv run mously
```

Run the tests:

```bash
uv run pytest
```

## License

GPL-2.0-or-later. See [LICENSE](LICENSE).

The private macOS gesture-event serialization in `mously/macos.py` is adapted
from `tl_CGEventCreateFromGesture` in Calf Trail Software's
[Touch](https://github.com/calftrail/Touch) project, copyright 2010 Calf Trail
Software, LLC, and distributed under GPL-2.0-or-later.
