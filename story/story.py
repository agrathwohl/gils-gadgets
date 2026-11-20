#!/usr/bin/env python3
"""
Story - Gil tells a story, and the pictures of its words move on the screen
"""

import _thread
import argparse
import curses
import math
import queue
import random
import re
import subprocess
import sys
import threading
import time
import tomllib
from pathlib import Path

import pyfiglet

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "screen-saver"))
from screensaver import COLORS, EFFECTS, FRAME_MS, Item, move, scroll  # noqa: E402

FOLDERS = ["typing-game/assets/ascii", "musical-keyboard/assets/ascii", "screen-saver/pictures", "story/pictures"]
QUIET = 180  # seconds with no known phrase, then the story is cleared and hides
SAY = 8  # seconds for each sentence of --say
TEXT_ROWS = 10  # at the bottom, for the sentence in big letters
DOTS = [(0, 0), (1, 0), (2, 0), (0, 1), (1, 1), (2, 1), (3, 0), (3, 1)]  # (row, column) of each bit of a Braille cell

# Each picture is a thing. Its word is the file name without a number at the end, with - as a space:
# cat2.txt is "cat", drum-kit-1.txt is "drum kit". A word can have many pictures; the story picks one at random.
PICTURES = {}
for path in sorted(p for folder in FOLDERS for p in (ROOT / folder).glob("*.txt")):
    PICTURES.setdefault(re.sub(r"-?\d+$", "", path.stem).replace("-", " ").lower(), []).append(path)
PICTURE_COLORS = tomllib.loads((ROOT / "story/pictures/colors.toml").read_text())
WORDS = tomllib.loads((ROOT / "story/words.toml").read_text())
ALIASES, ACTIONS, DESCRIPTIONS = WORDS["aliases"], WORDS["actions"], WORDS["descriptions"]
FORMS = {form: name for name, action in ACTIONS.items() for form in action["says"]}


# The moves of the story are effects too (see screensaver.py). In a scene with two things, item.side is 1 for the
# thing on the left and -1 for the one on the right; alone, it is 0.

def arrive(cells, t, item):
    return move(cells, 0, min(0, 2 * (t % 100) - item.spare_x // 2 - item.w))


def up(cells, t, item):
    return move(cells, item.h + item.spare_y - item.spare_y // 2 - t % (2 * item.h + item.spare_y), 0)


def down(cells, t, item):
    return move(cells, t % (2 * item.h + item.spare_y) - item.h - item.spare_y // 2, 0)


def toward(cells, item, p, size):
    """The cells p of the way to the middle, where the two things touch, and size times as big:
    a thing gets smaller toward its side next to the other thing, so that it goes in there."""
    cy, cx, dx = item.h / 2, (1 + item.side) * item.w / 2, item.side * (item.spare_x // 2)
    return [(round(cy + (y - cy) * size), round(cx + (x - cx) * size + p * dx), ch, color, col)
            for y, x, ch, color, col in cells]


def ramp(t):
    return min(1, t % 100 / 30)  # from 0 to 1 in 3 seconds, then 1 for 7 seconds


def in_(cells, t, item):
    return toward(cells, item, ramp(t), 1 - ramp(t)) if ramp(t) < 1 else []


def out(cells, t, item):
    return toward(cells, item, 1 - ramp(t), ramp(t))


def hug(cells, t, item):
    return toward(cells, item, ramp(t), 1)


MOVES = EFFECTS | {"across": scroll, "arrive": arrive, "up": up, "down": down, "in": in_, "out": out, "hug": hug}


def scale(lines, f):
    """A Braille picture f times as big: each dot covers the dots under it in the new picture,
    so with f = 0.5, 2 x 2 dots become 1 dot."""
    def span(n):
        return range(int(n * f), max(int(n * f) + 1, int((n + 1) * f)))

    cells = {}
    for y, line in enumerate(lines):
        for x, ch in enumerate(line):
            for bit, (dy, dx) in enumerate(DOTS):
                if ch != " " and (ord(ch) - 0x2800) >> bit & 1:
                    for r in span(4 * y + dy):
                        for c in span(2 * x + dx):
                            cells[r // 4, c // 2] = cells.get((r // 4, c // 2), 0) | 1 << DOTS.index((r % 4, c % 2))
    h, w = math.ceil(len(lines) * f), math.ceil(max(map(len, lines)) * f)
    return ["".join(chr(0x2800 + cells[y, x]) if (y, x) in cells else " " for x in range(w)).rstrip() for y in range(h)]


def phrases():
    """Everything that the story knows, as Gil says it"""
    return sorted({*PICTURES, *ALIASES, *FORMS, *DESCRIPTIONS})


def known(text):
    """The known phrases of a text in order, the longest first ("cat in the hat", not "cat"), like listen()"""
    words, every, found, i = re.findall(r"[a-z']+", text.lower()), set(phrases()), [], 0
    while i < len(words):
        n = next((n for n in range(len(words) - i, 0, -1) if " ".join(words[i:i + n]) in every), 0)
        if n:
            found.append(" ".join(words[i:i + n]))
        i += n or 1
    return found


def spelled(heard):
    """The phrases as the story shows them: an alias of an alias is another way to hear it ("gill" is "gil")"""
    return [ALIASES[phrase] if ALIASES.get(phrase) in ALIASES else phrase for phrase in heard]


def merge(*changes):
    """Changes together: the effects add up, the speeds multiply, and else the last one counts"""
    merged = {"effects": [], "speed": 1}
    for change in changes:
        merged = merged | change | {"effects": merged["effects"] + change.get("effects", []),
                                    "speed": merged["speed"] * change.get("speed", 1)}
    return merged


def parse(heard, hero=None):
    """The scene of a sentence, from its known phrases in order: the first one or two things with their changes,
    and the changes of the first action. A thing description goes to the next thing, or to the first thing
    when no thing comes after it. An action description goes to the action. A sentence with no thing before
    its action is about the hero, the first thing of the sentence before: "the dog", then "jumps"."""
    things, action, waiting, moves = [], {}, [], []
    for phrase in heard:
        word = ALIASES.get(phrase, phrase)
        word = ALIASES.get(word, word)
        if word in PICTURES:
            things.append((word, merge(*waiting)))
            waiting = []
        elif phrase in FORMS:
            if hero and not things:
                things.append(hero)
            action = action or {"name": FORMS[phrase]} | ACTIONS[FORMS[phrase]]
        elif phrase in DESCRIPTIONS:
            (waiting if DESCRIPTIONS[phrase]["to"] == "thing" else moves).append(DESCRIPTIONS[phrase])
    if hero and not things:
        things.append(hero)
    if things and waiting:
        things[0] = (things[0][0], merge(things[0][1], *waiting))
    return things[:2], merge(action, *moves)


def layout(story, pictures, h, w):
    """The items on the screen for the last sentence of the story: the story so far in the top row,
    the scene, and the sentence in big letters at the bottom. pictures keeps the picture of each word,
    so that a thing looks the same in the whole story."""
    sentence, hero = story[-1] if story else ["story"], None
    for heard in story or [sentence]:
        things, action = parse(heard, hero)
        hero = things[0] if things else hero
    top, height = 2, h - 2 - TEXT_ROWS
    shown = []
    for word, changes in things:
        path = pictures.setdefault(word, random.choice(PICTURES[word]))
        text = path.read_text().expandtabs(8).replace("\u2800", " ")
        lines = [line.rstrip() for line in text.strip("\n").split("\n")]
        braille = all("\u2800" <= ch <= "\u28ff" for ch in text if ch not in " \n")
        if braille and changes.get("size") == "small":
            lines = scale(lines, 0.5)
        shown.append((lines, braille, changes, changes.get("color", PICTURE_COLORS.get(path.stem, "white"))))
    if len(shown) == 2 and max(len(line) for lines, *_ in shown for line in lines) > w // 2:
        shown = shown[:1]  # too wide for half the screen: the first thing shows alone
    box, items = w // max(1, len(shown)), []
    for i, (lines, braille, changes, color) in enumerate(shown):
        f = min(2, box / max(map(len, lines)), height / len(lines))
        if braille and changes.get("size") == "big" and f > 1:
            lines = scale(lines, f)
        item = Item(lines[:height], {"color": color})  # a picture that is too tall loses its bottom rows
        names = [action.get("move"), *action["effects"]] if i == 0 else action.get("other", [])
        item.effects = [MOVES[name] for name in names + changes["effects"] if name]
        item.place(top, i * box, height, box)
        item.side = (1, -1)[i] if len(shown) == 2 else 0
        items.append(item)
    so_far = ". ".join(" ".join(s) for s in story[:-1]).upper()
    said = "   ".join(sentence).upper()  # the big letters have narrow spaces
    big = pyfiglet.figlet_format(said, font="big", width=w).rstrip("\n").split("\n")
    texts = [Item([so_far[-w:]], {}), Item(big if len(big) <= TEXT_ROWS else [said], {})]
    texts[0].place(0, 0, 1, w)
    texts[1].place(h - TEXT_ROWS, 0, TEXT_ROWS, w)
    return items + texts, action["speed"]


def show(stdscr, sentences, live):
    """Shows a scene for each sentence from the queue, until Esc (any key, if not live) or QUIET seconds
    with no known phrase"""
    curses.curs_set(0)
    curses.start_color()
    curses.use_default_colors()
    attrs = {}
    for i, name in enumerate(COLORS, 1):
        curses.init_pair(i, getattr(curses, "COLOR_" + name.upper()), -1)
        attrs[name] = curses.color_pair(i) | curses.A_BOLD
    stdscr.timeout(FRAME_MS)
    story, pictures, size, heard, t = [], {}, None, time.monotonic(), 0
    while time.monotonic() - heard < QUIET:
        try:
            sentence = sentences.get_nowait()
        except queue.Empty:
            sentence = None
        if sentence and sentence != "story":  # while the story shows, "story" is an unknown word
            story.append(spelled(sentence))
            size, heard, t = None, time.monotonic(), 0
        if stdscr.getmaxyx() != size:
            size = stdscr.getmaxyx()
            items, speed = layout(story, pictures, *size)
        stdscr.erase()
        for item in items:
            item.draw(stdscr, int(t * speed), attrs)
        stdscr.refresh()
        key = stdscr.getch()
        if key == 27 or not live and key not in (-1, curses.KEY_RESIZE):
            return
        t += 1


def say(sentences, texts):
    for text in texts:
        sentences.put(known(text))
        time.sleep(SAY)


def fgconsole():
    return subprocess.run(["fgconsole"], capture_output=True, text=True).stdout.strip()


def live(wait, vt):
    """Listens to the microphone and shows the story. With wait, it hides on console vt and writes nothing
    there (the screen saver counts writes) until Gil says "story"."""
    from listen import listen  # it needs sherpa-onnx and the models: only here

    sentences, awake = queue.Queue(), threading.Event()

    def hear():
        try:
            for heard in listen(phrases(), awake):
                sentences.put(heard)
        finally:
            _thread.interrupt_main()  # without its ears, the story stops (on the Pi, the login starts it again)

    threading.Thread(target=hear, daemon=True).start()
    if not wait:  # alone on tty1: it always shows
        awake.set()
        while True:
            curses.wrapper(show, sentences, True)
    back = "1"  # the console to switch back to
    while True:
        try:
            heard = sentences.get(timeout=2)
        except queue.Empty:
            heard = None
        front = fgconsole()
        if heard == "story":
            if front != vt:
                back = front
            subprocess.run(["chvt", vt])
            awake.set()
            curses.wrapper(show, sentences, True)
            awake.clear()
            if fgconsole() == vt:  # else Gil pressed a MIDI key, and the musical keyboard has the screen now
                subprocess.run(["chvt", back])
                back = "1"  # the saved console was for this story only
        elif front == vt:  # the musical keyboard went back to this console, or the story restarted after a crash
            subprocess.run(["chvt", back])


def check():
    assert len(PICTURES["cat"]) >= 4 and "drum kit" in PICTURES and "cat in the hat" in PICTURES, "picture words"
    assert scale(["⣿⣿", "⣿⣿"], 0.5) == ["⣿"] and scale(["⣿"], 2) == ["⣿⣿", "⣿⣿"], "scale"
    for alias, thing in ALIASES.items():
        assert ALIASES.get(thing, thing) in PICTURES, f"alias {alias!r}: there is no picture of {thing!r}"
        assert parse([alias])[0][0][0] == ALIASES.get(thing, thing), f"alias {alias!r}: parse"
        assert spelled([alias]) == [thing if thing in ALIASES else alias], f"alias {alias!r}: spelled"
    said = [*PICTURES, *ALIASES, *FORMS, *DESCRIPTIONS]
    assert len(said) == len(set(said)), f"words in two places: {sorted({p for p in said if said.count(p) > 1})}"
    for name, change in [*ACTIONS.items(), *DESCRIPTIONS.items()]:
        for effect in [change.get("move"), *change.get("effects", []), *change.get("other", [])]:
            assert effect is None or effect in MOVES, f"{name}: unknown move or effect {effect!r}"
        assert change.get("color", "white") in COLORS, f"{name}: unknown color {change['color']!r}"
        assert change.get("to", "action") in ("thing", "action"), f"{name}: to must be \"thing\" or \"action\""
    for stem, color in PICTURE_COLORS.items():
        assert color in COLORS, f"colors.toml: {stem}: unknown color {color!r}"

    def scene(things, action):  # in words: each thing with its size, color and effects / the action and its move
        speed = action["speed"] != 1 and f"x{action['speed']:g}"
        return (", ".join(" ".join(filter(None, [c.get("size"), c.get("color"), *c["effects"], word]))
                          for word, c in things) or "-") + " / " + (
            " ".join(filter(None, [action.get("name"), action.get("move"), speed])) or "-")

    samples = [
        ("the dog jumps up", "dog / jumps up"),
        ("the cat eats the big banana", "cat, big banana / eats"),
        ("the dog is big", "big dog / -"),
        ("the cat in the hat goes in the house", "cat in the hat, house / goes in"),
        ("doggy runs fast", "dog / runs across x4"),
        ("the purple cow sleeps", "magenta cow / sleeps float x0.5"),
        ("the pink pig dances", "magenta pig / dances float x2"),
        ("mommy hugs daddy", "mom, dad / hugs hug"),
        ("the dog sees the cat and the cow", "dog, cat / sees"),
        ("the bunny jumps and runs", "bunny / jumps bounce"),
        ("the small tiger sees the dog", "small tiger, dog / sees"),
        ("the choo choo train goes", "train / goes across"),
        ("the frog comes out of the pond", "frog / comes out"),
        ("the happy duck swims slow", "sparkle duck / swims across x0.5"),
        ("big red", "- / -"),
        ("story", "- / -"),
        ("the boy plays the drum kit", "boy, drum kit / plays bounce"),
        ("the cold penguin helps the polar bear", "cyan shake penguin, polar bear / helps float"),
        ("the silly monkey falls down", "shake monkey / falls down"),
        ("the girl and the big red dog share the cake", "girl, big red dog / shares"),
    ]
    for text, want in samples:
        got = scene(*parse(known(text)))
        assert got == want, f"{text!r}: {got!r}, not {want!r}"
    hero = parse(known("the big dog"))[0][0]
    for text, want in [("jumps up", "big dog / jumps up"), ("eats the banana", "big dog, banana / eats"),
                       ("small", "small dog / -"), ("the cat sleeps", "cat / sleeps float x0.5")]:
        got = scene(*parse(known(text), hero))
        assert got == want, f"after \"the big dog\", {text!r}: {got!r}, not {want!r}"
    print(f"All right: {len(samples)} sentences, {len(phrases())} phrases")


def main():
    parser = argparse.ArgumentParser(description="Story")
    parser.add_argument("--check", action="store_true",
                        help="run sample sentences through the parser, and check the words")
    parser.add_argument("--phrases", action="store_true", help="print the phrases that the story knows, one per line")
    parser.add_argument("--say", action="append", metavar="SENTENCE",
                        help="show this sentence, without the microphone (again for more sentences, one after another)")
    parser.add_argument("--wait", action="store_true",
                        help="hide, and show the story when Gil says \"story\" (for the Pi image, with --vt)")
    parser.add_argument("--vt", default="4", help="the console of the story with --wait (default: 4)")
    args = parser.parse_args()

    if args.check:
        check()
    elif args.phrases:
        print("\n".join(phrases()))
    elif args.say:
        sentences = queue.Queue()
        threading.Thread(target=say, args=(sentences, args.say), daemon=True).start()
        curses.wrapper(show, sentences, False)
    else:
        try:
            live(args.wait, args.vt)
        except KeyboardInterrupt:  # Ctrl+C, or the listener stopped
            sys.exit(1)


if __name__ == "__main__":
    main()
