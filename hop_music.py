#!/usr/bin/env python3
"""HomeOS Plus Music: plays .hs (HomeOS Song) files.

A .hs file is plain text. Lines starting with # are comments.

    tempo=120        beats per minute (optional, default 120)
    octave=4         base octave (optional, default 4)
    C D E F G A B    one note each, one beat each
    C#  Eb           sharps and flats
    r                rest, one beat
    C1               chord: a letter + number is a chord on that root

Chord numbers (the root letter picks the chord, the number picks the kind):
    1 minor          2 major          3 dominant 7th    4 major 7th
    5 minor 7th      6 diminished     7 augmented

Example:
    tempo=100
    C E G C2 G2 C1 F2 G3 C2

Playback uses aplay when present; --export saves a .wav instead.
"""
import math
import os
import shutil
import struct
import subprocess
import sys
import wave

SEMITONES = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
CHORDS = {
    1: ("minor", [0, 3, 7]),
    2: ("major", [0, 4, 7]),
    3: ("dominant 7th", [0, 4, 7, 10]),
    4: ("major 7th", [0, 4, 7, 11]),
    5: ("minor 7th", [0, 3, 7, 10]),
    6: ("diminished", [0, 3, 6]),
    7: ("augmented", [0, 4, 8]),
}
RATE = 22050


class SongError(ValueError):
    pass


def note_freq(name, octave):
    """name like C, C#, Eb; octave int. Returns Hz."""
    if len(name) >= 2 and name[1] == "#":
        semi = SEMITONES[name[0].upper()] + 1
    elif len(name) >= 2 and name[1].lower() == "b":
        semi = SEMITONES[name[0].upper()] - 1
    else:
        semi = SEMITONES[name[0].upper()]
    midi = 12 * (octave + 1) + semi
    return 440.0 * (2.0 ** ((midi - 69) / 12.0))


def parse_song(text):
    """Returns {tempo, octave, events:[{freqs:[hz], beats:1} or {rest:True}]}"""
    tempo, octave, events = 120, 4, []
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if line.lower().startswith("tempo="):
            try:
                tempo = int(line.split("=", 1)[1])
            except ValueError:
                raise SongError("bad tempo line: %r" % raw)
            if not 30 <= tempo <= 300:
                raise SongError("tempo must be 30-300, got %d" % tempo)
            continue
        if line.lower().startswith("octave="):
            try:
                octave = int(line.split("=", 1)[1])
            except ValueError:
                raise SongError("bad octave line: %r" % raw)
            if not 1 <= octave <= 7:
                raise SongError("octave must be 1-7, got %d" % octave)
            continue
        for tok in line.split():
            events.append(parse_token(tok, octave))
    if not events:
        raise SongError("no notes in this song")
    return {"tempo": tempo, "octave": octave, "events": events}


def parse_token(tok, octave):
    if tok.lower() == "r":
        return {"rest": True, "beats": 1}
    letter = tok[0].upper()
    if letter not in SEMITONES:
        raise SongError("unknown note %r - use A B C D E F G (or r to rest)" % tok)
    rest = tok[1:]
    accidental = ""
    if rest.startswith("#"):
        accidental, rest = "#", rest[1:]
    elif rest.startswith("b"):
        accidental, rest = "b", rest[1:]
    name = letter + accidental
    if rest == "":
        return {"freqs": [note_freq(name, octave)], "beats": 1}
    if not rest.isdigit():
        raise SongError("bad token %r - after the note use a chord number 1-7" % tok)
    kind = int(rest)
    if kind not in CHORDS:
        raise SongError("unknown chord number %d in %r - use 1-7 "
                        "(1 minor, 2 major, 3 dom7, 4 maj7, 5 min7, 6 dim, 7 aug)"
                        % (kind, tok))
    _, intervals = CHORDS[kind]
    base = note_freq(name, octave)
    freqs = [base * (2.0 ** (i / 12.0)) for i in intervals]
    return {"freqs": freqs, "beats": 1}


def synth(events, tempo, rate=RATE):
    """Mix all events into 16-bit mono samples (list of ints)."""
    beat = 60.0 / tempo
    out = []
    for ev in events:
        n = int(beat * ev["beats"] * rate)
        if ev.get("rest"):
            out.extend([0] * n)
            continue
        freqs = ev["freqs"]
        for i in range(n):
            t = i / rate
            env = min(1.0, t / 0.01) * (1.0 - (i / n) ** 3)
            sample = sum(math.sin(2 * math.pi * f * t) for f in freqs) / len(freqs)
            out.append(int(12000 * env * sample))
    return out


def write_wav(path, samples, rate=RATE):
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"".join(struct.pack("<h", s) for s in samples))


def play(samples, rate=RATE):
    aplay = shutil.which("aplay")
    if not aplay:
        return False
    raw = b"".join(struct.pack("<h", s) for s in samples)
    subprocess.run([aplay, "-q", "-r", str(rate), "-f", "S16_LE", "-c", "1"],
                   input=raw, check=False)
    return True


def describe(song):
    lines = ["tempo %d, octave %d, %d events" % (song["tempo"], song["octave"],
                                                 len(song["events"]))]
    beats = sum(e["beats"] for e in song["events"])
    lines.append("about %.1f seconds" % (beats * 60.0 / song["tempo"]))
    return "\n".join(lines)


def pick_file(start_dir):
    songs = []
    for base, _dirs, files in os.walk(start_dir):
        for fn in sorted(files):
            if fn.lower().endswith(".hs"):
                songs.append(os.path.join(base, fn))
    if not songs:
        return None
    print("Songs:")
    for i, path in enumerate(songs, 1):
        print("  %d. %s" % (i, path))
    try:
        choice = input("Play which? [1] ").strip() or "1"
        return songs[int(choice) - 1]
    except (ValueError, IndexError):
        print("No such number.")
        return None
    except (EOFError, KeyboardInterrupt):
        return None


def main(argv):
    args = [a for a in argv[1:]]
    if "--export" in args:
        args.remove("--export")
        export = True
    else:
        export = False
    if not args:
        print(__doc__)
        picked = pick_file(os.path.expanduser("~"))
        if not picked:
            print("No .hs songs found. Save one, then run: hop_music.py song.hs")
            return 1
        args = [picked]
    path = args[0]
    try:
        with open(path, "r", encoding="utf-8") as fh:
            song = parse_song(fh.read())
    except OSError as exc:
        print("Cannot read %s: %s" % (path, exc))
        return 1
    except SongError as exc:
        print("Song problem: %s" % exc)
        return 2
    print(describe(song))
    samples = synth(song["events"], song["tempo"])
    if export:
        out = os.path.splitext(path)[0] + ".wav"
        write_wav(out, samples)
        print("saved %s" % out)
        return 0
    if not play(samples):
        print("aplay not found - use --export to save a .wav instead")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
