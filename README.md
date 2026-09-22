# Mously

[![License: GPL v2](https://img.shields.io/badge/license-GPL--2.0-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-green.svg)](https://www.python.org/)
![Platform](https://img.shields.io/badge/platform-macOS-lightgrey.svg)
![Network](https://img.shields.io/badge/network-self--hosted-blue.svg)

<p align="center">
  <img src="assets/mously-logo-v4.png" alt="Mously logo" width="240">
</p>

**Use your iPhone as a trackpad and media remote for your Mac.**

Mously is self-hosted on your Mac. There is no iPhone app to install, no
account, no cloud service, and no analytics. Just open the paired address in
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

To install Mously, simply run the following commands in your terminal:

```bash
uv tool install git+https://github.com/ericceg/mously.git
mously
```

On first launch, allow your terminal to control the Mac under **System Settings
→ Privacy & Security → Accessibility**, then restart Mously (use `Control-C` to stop it and run `mously` again).

Open the complete paired address printed in the terminal on an iPhone, typically
while both devices are connected to the same trusted Wi-Fi. Keep Mously running
while you use the remote; press `Control-C` to stop it.

It is also recommended to save the paired address to your iPhone's home screen for quick access. In Safari, tap the share button and select "Add to Home Screen".

Mously keeps the pairing token across restarts, so a saved home-screen app
continues to work. To invalidate the old address and pair again, run:

```bash
mously --reset-pairing
```

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

On first launch, Mously creates a random pairing token and stores it in
`~/Library/Application Support/Mously/pairing-token`. Only a browser opened
with the complete paired address can connect. The same token is reused across
restarts so bookmarks and home-screen apps keep working; use
`mously --reset-pairing` to revoke it.

**Important security note:**
Traffic is not encrypted. Mously listens on all IPv4 interfaces (`0.0.0.0`)
and does not technically enforce LAN-only access. Anyone who can reach the port
and obtains the complete paired address can control your Mac. Use Mously only
on networks you trust, check your firewall and router exposure, do not share the
address, and stop Mously when you are finished.

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

GPL-2.0-only. See [LICENSE](LICENSE).

The private macOS gesture-event serialization in `mously/macos.py` is adapted
from `tl_CGEventCreateFromGesture` in Calf Trail Software's
[Touch](https://github.com/calftrail/Touch) project, copyright 2010 Calf Trail
Software, LLC. Touch is licensed under GPL-2.0-or-later; Mously exercises the
GPL version-selection option and distributes the adaptation under
GPL-2.0-only. See
[Third-party notices](docs/third-party-notices.md) for source and licensing
details.
