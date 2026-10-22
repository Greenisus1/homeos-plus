#!/usr/bin/env python3
"""Unit tests for HomeOS Plus logic. No GUI, no root, no network."""
import json
import os
import sys
import tempfile

HERE = tempfile.mkdtemp(prefix="hop-test-")
os.environ["HOP_HOME"] = HERE
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import hop_common as hop  # noqa: E402

FAIL = []


def check(name, cond):
    print(("ok  " if cond else "FAIL") + " " + name)
    if not cond:
        FAIL.append(name)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write(text)


# dock config round-trip + clamping
cfg = hop.load_dock_config(os.path.join(HERE, "missing.json"))
check("defaults when config missing", cfg["position"] == "top" and cfg["size"] == 56
      and cfg["apps"] == [] and cfg["autohide"] is False)
saved = hop.save_dock_config({"position": "left", "size": 999, "autohide": 1,
                              "apps": ["a", "b"], "junk": True},
                             os.path.join(HERE, "dock.json"))
back = hop.load_dock_config(os.path.join(HERE, "dock.json"))
check("round-trip keeps values", back["position"] == "left" and back["apps"] == ["a", "b"])
check("size clamped to 128", back["size"] == 128)
check("autohide coerced to bool", back["autohide"] is True)
check("unknown keys dropped", "junk" not in back)
hop.save_dock_config({"position": "sideways", "size": "x"}, os.path.join(HERE, "bad.json"))
back = hop.load_dock_config(os.path.join(HERE, "bad.json"))
check("bad position falls back to top", back["position"] == "top")
check("bad size falls back to 56", back["size"] == 56)

# desktop file parsing + app listing
appsdir = os.path.join(HERE, "apps")
write(os.path.join(appsdir, "term.desktop"),
      "[Desktop Entry]\nName=Terminal\nExec=x-terminal-emulator\nIcon=utilities-terminal\n")
write(os.path.join(appsdir, "hidden.desktop"),
      "[Desktop Entry]\nName=Secret\nExec=secret\nNoDisplay=true\n")
write(os.path.join(appsdir, "broken.desktop"), "not a desktop file\n")
os.environ["HOP_DESKTOP_DIRS"] = appsdir
apps = hop.list_apps()
check("one visible app listed", [a["id"] for a in apps] == ["term"])
check("nodisplay app hidden", all(a["id"] != "hidden" for a in apps))
check("app fields parsed", apps[0]["name"] == "Terminal"
      and apps[0]["exec"] == "x-terminal-emulator")
del os.environ["HOP_DESKTOP_DIRS"]

check("clean_exec strips field codes",
      hop.clean_exec("foo %U --bar %f") == "foo --bar")
check("clean_exec tolerates empty", hop.clean_exec("") == "")

# themes
tdir = os.path.join(HERE, "themes")
os.makedirs(os.path.join(tdir, "PiXflat", "gtk-3.0"))
os.makedirs(os.path.join(tdir, "OldTwo", "gtk-2.0"))
os.makedirs(os.path.join(tdir, "NotATheme"))
check("theme listing finds gtk3+gtk2, skips plain dirs",
      hop.list_themes([tdir]) == ["OldTwo", "PiXflat"])

written = hop.apply_theme("PiXflat", home=HERE)
check("apply_theme writes two files", len(written) == 2 and all(os.path.exists(p) for p in written))
check("current_theme reads back", hop.current_theme(home=HERE) == "PiXflat")
hop.apply_theme("OldTwo", home=HERE)
check("re-apply replaces not duplicates", hop.current_theme(home=HERE) == "OldTwo")
with open(written[0]) as fh:
    check("only one gtk-theme-name line", fh.read().count("gtk-theme-name=") == 1)

# wallpaper config-file fallback (backend detection stubbed off for the test)
os.environ["HOP_FAKE_BACKENDS"] = ""
backend, detail = hop.apply_wallpaper("#2b6cb0", home=HERE)
check("wallpaper fallback uses config file", backend == "config-file")
with open(detail) as fh:
    check("wallpaper written to pcmanfm config", "wallpaper=#2b6cb0" in fh.read())
backend, detail = hop.apply_wallpaper("/tmp/pic.png", home=HERE)
with open(detail) as fh:
    check("re-apply replaces wallpaper line", fh.read().count("wallpaper=") == 1)

# wallpaper discovery
wdir = os.path.join(HERE, "walls")
write(os.path.join(wdir, "b.png"), "x")
write(os.path.join(wdir, "a.JPG"), "x")
write(os.path.join(wdir, "c.txt"), "x")
found = hop.list_wallpapers([wdir])
check("wallpaper list finds images sorted, skips text",
      [os.path.basename(p) for p in found] == ["a.JPG", "b.png"])

print()
if FAIL:
    print("%d FAILURES" % len(FAIL))
    sys.exit(1)
print("all unit tests passed")

# --- music app ----------------------------------------------------------
import hop_music as hm

song = hm.parse_song("tempo=100\noctave=4\nC E G r C2\n")
check("song parses tempo", song["tempo"] == 100)
check("song parses 5 events", len(song["events"]) == 5)
check("rest recognized", song["events"][3].get("rest") is True)
check("chord C2 is major triad", len(song["events"][4]["freqs"]) == 3)

check("A4 is 440Hz", abs(hm.note_freq("A", 4) - 440.0) < 0.01)
check("C4 about 261.6Hz", abs(hm.note_freq("C", 4) - 261.63) < 0.1)
check("C#4 is a semitone up", abs(hm.note_freq("C#", 4) / hm.note_freq("C", 4) - 2**(1/12)) < 0.001)
check("Eb4 equals D#4", abs(hm.note_freq("Eb", 4) - hm.note_freq("D#", 4)) < 0.01)

minor = hm.parse_token("C1", 4)["freqs"]
check("1 = minor (b3)", abs(minor[1] / minor[0] - 2**(3/12)) < 0.001)
major = hm.parse_token("C2", 4)["freqs"]
check("2 = major (3)", abs(major[1] / major[0] - 2**(4/12)) < 0.001)
check("3 = dominant 7th (4 notes)", len(hm.parse_token("C3", 4)["freqs"]) == 4)
check("7 = augmented", len(hm.parse_token("C7", 4)["freqs"]) == 3)

for bad, why in [("H", "unknown note"), ("C8", "chord 8 rejected"),
                 ("Cx", "bad suffix"), ("tempo=10\nC", "tempo too low")]:
    try:
        hm.parse_song(bad) if "=" in bad else hm.parse_token(bad, 4)
        check(why + " - should raise", False)
    except hm.SongError:
        check(why, True)

samples = hm.synth(song["events"], song["tempo"], rate=8000)
expect = int(60 / 100 * 8000) * 5
check("synth sample count matches beats", len(samples) == expect)
check("synth produces nonzero audio", any(s != 0 for s in samples))
wav_path = os.path.join(HERE, "out.wav")
hm.write_wav(wav_path, samples, rate=8000)
import wave as _wave
with _wave.open(wav_path) as w:
    check("wav valid", w.getframerate() == 8000 and w.getnchannels() == 1)
