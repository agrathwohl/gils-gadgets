#!/usr/bin/env python3
"""
Screen Saver - big words and pictures that move on the screen on a special day
"""

import argparse
import curses
import glob
import math
import os
import random
import sys
import time
import tomllib
from pathlib import Path

import pyfiglet

BASE_DIR = Path(__file__).parent
CONFIG = BASE_DIR / "screensavers.toml"
COLORS = ["red", "yellow", "green", "cyan", "blue", "magenta", "white"]
RAINBOW = COLORS[:6]
FRAME_MS = 100
TEXT_ROOM = 2  # more rows for each line of big text, so that it can move up and down


def last_activity():
    """The last time that a program read a key or wrote to the screen, on any console or terminal.
    The kernel keeps this time on each tty device file, in steps of 8 seconds."""
    paths = glob.glob("/dev/tty[0-9]*") + glob.glob("/dev/pts/[0-9]*")
    return max(max(st.st_atime, st.st_mtime) for st in map(os.stat, paths))


# An effect changes the cells of a line or a picture for frame t. A cell is (y, x, character, color, column):
# y and x are from the home position, and column is the column in the line or the picture.

def move(cells, dy, dx):
    return [(y + dy, x + dx, ch, color, col) for y, x, ch, color, col in cells]


def back_and_forth(n, top):
    if top <= 0:
        return 0
    n %= 2 * top
    return min(n, 2 * top - n)


def rainbow(cells, t, item):
    return [(y, x, ch, RAINBOW[(col // 4 - t) % len(RAINBOW)], col) for y, x, ch, _, col in cells]


def sparkle(cells, t, item):
    return [(y, x, "*", "white", col) if random.random() < 0.03 else (y, x, ch, color, col)
            for y, x, ch, color, col in cells]


def blink(cells, t, item):
    return cells if t % 20 < 14 else []


def wave(cells, t, item):
    a = min(2, item.spare_y // 2)
    return [(y + round(a * math.sin(col / 12 - t / 4)), x, ch, color, col) for y, x, ch, color, col in cells]


def float_(cells, t, item):
    return move(cells, round(min(2, item.spare_y // 2) * math.sin(t / 10)),
                round(min(3, item.spare_x // 2) * math.sin(t / 17)))


def bounce(cells, t, item):
    return move(cells, back_and_forth(t, item.spare_y) - item.spare_y // 2,
                back_and_forth(2 * t, item.spare_x) - item.spare_x // 2)


def scroll(cells, t, item):
    box = item.w + item.spare_x
    return move(cells, 0, box - (2 * t) % (box + item.w) - item.spare_x // 2)


def shake(cells, t, item):
    if t % 40 >= 10:
        return cells
    dy, dx = min(1, item.spare_y // 2), min(1, item.spare_x // 2)
    return move(cells, random.randint(-dy, dy), random.randint(-dx, dx))


def typewriter(cells, t, item):
    shown = (3 * t) % (item.w + 60)
    return [cell for cell in cells if cell[4] < shown]


def drop(cells, t, item):
    fall = item.spare_y // 2 + item.h
    return move(cells, min(0, 2 * (t % 100) - fall), 0)


EFFECTS = {
    "rainbow": rainbow, "sparkle": sparkle, "blink": blink, "wave": wave, "float": float_,
    "bounce": bounce, "scroll": scroll, "shake": shake, "typewriter": typewriter, "drop": drop,
}


class Item:

    def __init__(self, lines, settings):
        self.color = settings.get("color", "white")
        self.effects = [EFFECTS[name] for name in settings.get("effects", [])]
        self.h, self.w = len(lines), max(map(len, lines))
        self.cells = [(y, x, ch, self.color, x) for y, line in enumerate(lines) for x, ch in enumerate(line) if ch != " "]

    def place(self, top, left, height, width):
        self.box = top, left, height, width
        self.spare_y, self.spare_x = height - self.h, width - self.w

    def draw(self, win, t, attrs):
        cells = self.cells
        for effect in self.effects:
            cells = effect(cells, t, self)
        top, left, height, width = self.box
        y0, x0 = self.spare_y // 2, self.spare_x // 2
        for y, x, ch, color, _ in cells:
            if 0 <= y0 + y < height and 0 <= x0 + x < width:
                try:
                    win.addstr(top + y0 + y, left + x0 + x, ch, attrs[color])
                except curses.error:  # the bottom-right cell of the screen
                    pass


def make_items(saver, h, w):
    texts = [Item(pyfiglet.figlet_format(line["text"], font="big", width=w).rstrip("\n").split("\n"), line)
             for line in saver["lines"]]
    pictures = [Item((BASE_DIR / p["file"]).read_text().strip("\n").split("\n"), p)
                for p in saver.get("pictures", [])]
    text_h = sum(item.h + TEXT_ROOM for item in texts)
    y = 0 if pictures else max(0, (h - text_h) // 2)
    for item in texts:
        item.place(y, 0, item.h + TEXT_ROOM, w)
        y += item.h + TEXT_ROOM
    for i, item in enumerate(pictures):
        left, right = w * i // len(pictures), w * (i + 1) // len(pictures)
        item.place(y, left, h - y, right - left)
    return texts + pictures


def show(stdscr, saver):
    curses.curs_set(0)
    curses.start_color()
    curses.use_default_colors()
    attrs = {}
    for i, name in enumerate(COLORS, 1):
        curses.init_pair(i, getattr(curses, "COLOR_" + name.upper()), -1)
        attrs[name] = curses.color_pair(i) | curses.A_BOLD
    stdscr.timeout(FRAME_MS)
    size, t = None, 0
    while True:
        if stdscr.getmaxyx() != size:
            size = stdscr.getmaxyx()
            items = make_items(saver, *size)
        stdscr.erase()
        for item in items:
            item.draw(stdscr, t, attrs)
        stdscr.refresh()
        if stdscr.getch() not in (-1, curses.KEY_RESIZE):
            return
        t += 1


def load(name):
    savers = tomllib.loads(CONFIG.read_text())
    if name not in savers:
        sys.exit(f"There is no screen saver {name!r} in {CONFIG.name}. There are: {', '.join(savers)}")
    saver = savers[name]
    for item in saver["lines"] + saver.get("pictures", []):
        if item.get("color", "white") not in COLORS:
            sys.exit(f"{name}: unknown color {item['color']!r}. The colors are: {', '.join(COLORS)}")
        for effect in item.get("effects", []):
            if effect not in EFFECTS:
                sys.exit(f"{name}: unknown effect {effect!r}. The effects are: {', '.join(EFFECTS)}")
    return saver


def main():
    parser = argparse.ArgumentParser(description="Screen Saver")
    parser.add_argument("name", help="the name of a screen saver in screensavers.toml")
    parser.add_argument("--check", action="store_true",
                        help="do not show it: exit 0 if no key was pressed and no screen changed for "
                             "idle-minutes, else exit 1 (cron runs this first on the Pi)")
    args = parser.parse_args()

    saver = load(args.name)
    if args.check:
        sys.exit(0 if time.time() - last_activity() >= saver["idle-minutes"] * 60 else 1)
    curses.wrapper(show, saver)


if __name__ == "__main__":
    main()
