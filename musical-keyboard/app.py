#!/usr/bin/env python3
"""
Musical Keyboard - play MIDI instruments for a toddler, with ASCII art.

MIDI comes in through the ALSA sequencer (aseqdump) and is played by fluidsynth.
A program change on the MIDI keyboard selects the next instrument.
Any letter on the computer keyboard quits.
"""

import argparse
import curses
import os
import re
import subprocess
import threading
import time
from pathlib import Path

BASE_DIR = Path(__file__).parent
ART_DIR = BASE_DIR / "assets" / "ascii"
SOUNDFONT = BASE_DIR / "Timbres of Heaven GM_GS_XG_SFX V 3.4 Final.sf2"
SYNTH_OPTIONS = {
    "synth.polyphony": 128,
    "synth.cpu-cores": os.cpu_count(),
    # reverb/chorus off: good SF2s have the room baked in, the effects only add mud
    "synth.reverb.active": 0,
    "synth.chorus.active": 0,
    "synth.overflow.percussion": 4000,
    "synth.overflow.sustained": 600,
    "synth.overflow.released": -2000,
    "synth.overflow.age": 1000,
    "synth.overflow.volume": 500,
    "synth.gain": 0.8,
    "synth.threadsafe-api": 1,
    "synth.dynamic-sample-loading": 1,
}
KEYS_CHANNEL = 0
PADS_CHANNEL = 9  # GM drum channel (MIDI channel 10)

# (name, bank, program)
INSTRUMENTS = [
    ("violin", 0, 40),
    ("double bass", 0, 43),
    ("clarinet", 0, 71),
    ("oboe", 0, 68),
    ("bassoon", 0, 70),
    ("saxophone", 0, 65),
    ("trombone", 0, 57),
    ("trumpet", 0, 56),
    ("tuba", 0, 58),
    ("grand piano", 0, 0),          # Concert Grand
    ("drum kit 1", 128, 0),         # Don's Standard
    ("drum kit 2", 128, 8),         # Room
    ("drum kit 3", 128, 16),        # Power
    ("drum kit 4", 128, 32),        # Jazz
    ("percussion 1", 128, 48),      # Orchestra
    ("percussion 2", 128, 50),      # Symphony
    ("sound fx", 128, 56),          # GM2 SFX
    ("electronic kit 1", 128, 24),  # Electronic
    ("electronic kit 2", 128, 25),  # TR-808
    ("electronic kit 3", 128, 26),  # TR-909
    ("electronic kit 4", 128, 27),  # Dance
]
DEFAULT_KIT = [name for name, _, _ in INSTRUMENTS].index("drum kit 1")  # pads play it while a melodic instrument is selected
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# aseqdump line, e.g. " 24:0   Note on                 0, note 60, velocity 100"
EVENT_RE = re.compile(r"(Note on|Note off|Control change|Program change|Pitch bend)\s+(\d+), \w+ (-?\d+)(?:, \w+ (\d+))?")


class Player:
    def __init__(self, port):
        self.port = port
        self.index = 0
        self.held = ()  # sorted MIDI notes of the keys held down now
        self.played = threading.Event()
        self.dump = None  # the aseqdump process that reads the MIDI keyboard
        self.synth = subprocess.Popen(
            ["fluidsynth", "-q", "-n", "-a", "alsa",
             *[arg for key, value in SYNTH_OPTIONS.items() for arg in ("-o", f"{key}={value}")], str(SOUNDFONT)],
            stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, text=True,
        )
        self.select(0)

    def send(self, command):
        self.synth.stdin.write(command + "\n")
        self.synth.stdin.flush()

    def select(self, index):
        self.index = index
        _, bank, prog = INSTRUMENTS[index]
        self.send(f"select {KEYS_CHANNEL} 1 {bank} {prog}")
        _, bank, prog = INSTRUMENTS[index if bank == 128 else DEFAULT_KIT]
        self.send(f"select {PADS_CHANNEL} 1 {bank} {prog}")

    def handle(self, line):
        m = EVENT_RE.search(line)
        if not m:
            return
        event, chan, a, b = m.group(1), int(m.group(2)), int(m.group(3)), m.group(4)
        ch = PADS_CHANNEL if chan == PADS_CHANNEL else KEYS_CHANNEL
        if event == "Note on" and int(b):
            self.send(f"noteon {ch} {a} {b}")
            if ch == KEYS_CHANNEL:
                self.held = tuple(sorted({*self.held, a}))
            self.played.set()
        elif event in ("Note on", "Note off"):
            self.send(f"noteoff {ch} {a}")
            if ch == KEYS_CHANNEL:
                self.held = tuple(n for n in self.held if n != a)
        elif event == "Control change":
            self.send(f"cc {ch} {a} {b}")
        elif event == "Pitch bend":
            self.send(f"pitch_bend {ch} {a + 8192}")
        elif event == "Program change":
            self.select((self.index + 1) % len(INSTRUMENTS))

    def listen(self):
        """Read MIDI forever; reconnect when the keyboard is unplugged or not there yet."""
        while True:
            self.dump = subprocess.Popen(["aseqdump", "-p", self.port],
                                         stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
            for line in self.dump.stdout:
                self.handle(line)
            self.dump.wait()
            time.sleep(1)


def load_art(index):
    path = ART_DIR / (INSTRUMENTS[index][0].replace(" ", "-") + ".txt")
    return path.read_text().strip("\n").split("\n") if path.exists() else []


def draw(win, lines, notes):
    win.erase()
    h, w = win.getmaxyx()
    width = max((len(line) for line in lines), default=0)
    y0, x0 = max(0, (h - len(lines) - 2) // 2), max(0, (w - width) // 2)
    text = " ".join(NOTE_NAMES[n % 12] for n in notes)
    rows = [(y0 + i, x0, line[:w - x0], 0) for i, line in enumerate(lines)]
    rows.append((min(y0 + len(lines) + 1, h - 1), max(0, (w - len(text)) // 2), text[:w], curses.A_BOLD))
    for y, x, s, attr in rows:
        try:
            win.addstr(y, x, s, attr)
        except curses.error:  # off screen or bottom-right cell
            pass
    win.refresh()


def run_ui(stdscr, player):
    curses.curs_set(0)
    stdscr.timeout(30)
    shown = None
    while True:
        state = (player.index, player.held)
        if state != shown:
            if not shown or shown[0] != state[0]:
                art = load_art(state[0])
            shown = state
            draw(stdscr, art, state[1])
        key = stdscr.getch()
        if key == curses.KEY_RESIZE:
            shown = None
        elif 0 <= key < 256 and chr(key).isalpha():
            return


def main():
    parser = argparse.ArgumentParser(description="Musical Keyboard")
    parser.add_argument("--port", default="MPK mini", help="ALSA sequencer MIDI port (default: MPK mini)")
    parser.add_argument("--wait", action="store_true",
                        help="daemon mode: show the app on the first MIDI key press, wait again after it quits")
    parser.add_argument("--vt", type=int,
                        help="switch to this virtual console while the app shows, then back (for the Pi image)")
    args = parser.parse_args()

    player = Player(args.port)
    threading.Thread(target=player.listen, daemon=True).start()
    try:
        while True:
            if args.wait:
                player.played.clear()
                player.played.wait()
            if args.vt:
                back = subprocess.run(["fgconsole"], capture_output=True, text=True).stdout.strip()
                subprocess.run(["chvt", str(args.vt)])
            curses.wrapper(run_ui, player)
            if args.vt:
                subprocess.run(["chvt", back])
            if not args.wait:
                break
    except KeyboardInterrupt:
        pass
    finally:
        player.synth.terminate()
        if player.dump:  # else aseqdump outlives the app
            player.dump.terminate()


if __name__ == "__main__":
    main()
