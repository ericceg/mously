# Third-Party Notices

## Touch gesture-event serialization

The private macOS gesture-event serialization in `mously/macos.py`, primarily
the `_create_magnify_event` implementation and its supporting event-data
structures, is a Python adaptation of `tl_CGEventCreateFromGesture` from:

- Project: [Touch](https://github.com/calftrail/Touch)
- Source: [`TouchSynthesis/TouchEvents.c`](https://github.com/calftrail/Touch/blob/master/TouchSynthesis/TouchEvents.c)
- Copyright: Copyright (C) 2010 Calf Trail Software, LLC
- Original license: GNU General Public License, version 2 or (at the recipient's
  option) any later version (`GPL-2.0-or-later`)

The upstream GitHub repository does not currently contain a standalone license
file. The licensing provenance is documented by these public sources:

- [Nathan Vander Wilt's explanation of the Touch code and its GPL license](https://stackoverflow.com/a/21096942)
- [Hammerspoon's preserved GPL-2.0-or-later notice for the same Touch component](https://github.com/Hammerspoon/hammerspoon/blob/master/extensions/eventtap/eventtap.lua)

Mously exercises the GPL version-selection option and distributes its adapted
implementation under `GPL-2.0-only`. The full GPL version 2 license text is in
the repository's `LICENSE` file.

The adaptation was introduced on 2026-09-20 and has been modified since then.
