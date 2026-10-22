# HomeOS Plus

A custom desktop for Home Pi (and Raspberry Pi OS Lite) with its own launcher
dock: **Terminal and Exit first**, then App Store, Settings, and the apps you
pick. One install turns the console into an autologin graphical desktop;
uninstall brings the console boot back.

Built with AI assistance from my design.

## What you get

- **Terminal app** - always the first button on the dock.
- **Exit app** - always second. Quits the desktop back to the console
  (asks first; the console is also always on Ctrl+Alt+F1).
- **App Store button** - opens the Pi App Store in a terminal, or shows the
  two commands to add it.
- **Settings app** - customize without admin knowledge:
  - wallpaper: solid colours, the Pi's built-in pictures, or any image file
  - theme: every installed GTK theme, one click
  - dock: top / bottom / left / right, button size, auto-hide
  - apps: tick which installed apps appear on the dock

Underneath is the official Raspberry Pi Desktop (PIXEL on Wayland), so real
desktop apps just work. HomeOS Plus is the friendly layer on top.

## Install

From the Pi App Store (Desktop Apps section), or by hand:

```sh
bash app-store.sh install
```

The install asks before rebooting. Nothing is automatic until you say yes.
Everything is free; the desktop packages come from the normal Raspberry Pi OS
repositories.

## Remove

```sh
bash app-store.sh uninstall
```

Boot goes back to the console. The desktop packages stay installed (they are
harmless on disk); the uninstaller prints the one command that removes them
too.

## Honest notes

- Pi 5 is the main target. A Pi 3A+ can run the desktop but it is slow -
  usable for the dock and terminal, not for heavy apps.
- The desktop download is large (a few hundred MB); first install takes
  several minutes.
- Install does not touch Home Pi's console launcher or any other app.
  The desktop runs on its own screen; Ctrl+Alt+F1 always gets you back.

MIT license.

## Music (.hs songs)

The Music app plays HomeOS Song files (`.hs`) - a tiny text format where
letters are notes:

```
tempo=120        # beats per minute (optional)
octave=4         # base octave (optional)
C D E F G A B    # one note each, one beat each
C#  Eb           # sharps and flats
r                # rest
C1               # a letter + number is a chord on that root
```

Chord numbers: **1** minor, **2** major, **3** dominant 7th, **4** major 7th,
**5** minor 7th, **6** diminished, **7** augmented.

Run `python3 hop_music.py song.hs` to play, `--export` to save a .wav, or
open the Music app and pick from your songs. An example lives in
`examples/twinkle.hs`.

## Ubuntu apps

Pi OS is Debian-based, so most Ubuntu apps install fine. In Settings, the
Apps tab has "Install an Ubuntu app (.deb file)..." - pick a downloaded
arm64 .deb and a terminal opens to install it with apt. Not every Ubuntu
package works on Pi OS; if apt refuses it, that app is not compatible.

## Files

- `app-store.sh` / `homeos-plus.sh` - install, uninstall, status
- `hop_dock.py` - the launcher dock (Terminal, Exit, App Store, Music, Settings, your picks)
- `hop_settings.py` - wallpaper, theme, dock layout, dock apps, .deb installs
- `hop_music.py` - the .hs song player
- `tests/` - unit and PTY tests (`sh tests/run-tests.sh`)
