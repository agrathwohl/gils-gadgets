"""Make the story pictures that are not there yet: download each Noto Emoji in emoji.toml, turn it into a
Braille line picture (edges of the colors and of the outline), and write story/pictures/<word>.txt and its
color in colors.toml. To make a picture again, delete its file. --check only looks at the files (no downloads).
Usage: uv run --with pillow python story/scripts/make_pictures.py [--check]"""
import colorsys
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path
from PIL import Image, ImageChops, ImageFilter, ImageOps

# The commit of the tag v2026-09-24-unicode18_0 (a tag can move)
URL = "https://raw.githubusercontent.com/googlefonts/noto-emoji/e20cbc2bbec1926686be9f9bee7d1d2cfa1fea0e/2D/png/512/emoji_u%s.png"
PICTURES = Path(__file__).resolve().parent.parent / "pictures"
COLS, MAX_COLS, MAX_ROWS = 80, 102, 54  # a picture must fit one of two boxes on the screen
SCALE = 4  # find the edges at 4x the dot size, then a dot is on when its 4x4 block has an edge
HUES = [(16, "red"), (60, "yellow"), (165, "green"), (200, "cyan"), (260, "blue"), (335, "magenta"), (360, "red")]  # hues (degrees) up to the number
BITS = [(0, 0, 0x01), (0, 1, 0x02), (0, 2, 0x04), (1, 0, 0x08), (1, 1, 0x10), (1, 2, 0x20), (0, 3, 0x40), (1, 3, 0x80)]


def main_color(img):
    """The color that covers most of the opaque, saturated pixels; white when there are few of those."""
    count, opaque = {}, 0
    for n, (r, g, b, a) in img.resize((128, 128)).getcolors(128 * 128):
        if a < 128:
            continue
        opaque += n
        hue, light, sat = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
        if sat >= 0.25 and light <= 0.85:
            name = next(name for top, name in HUES if hue * 360 < top)
            count[name] = count.get(name, 0) + n
    best = max(count, key=count.get, default="white")
    return best if count.get(best, 0) > opaque * 0.2 else "white"


def braille(img, cols):
    w, h = cols * 2, round(cols * 2 * img.height / img.width / 4) * 4  # a Braille dot is about square
    big = img.resize((w * SCALE, h * SCALE), Image.LANCZOS)
    alpha = big.getchannel("A").point(lambda a: 255 if a > 128 else 0)
    on_white = Image.alpha_composite(Image.new("RGBA", big.size, "white"), big).convert("L")
    inner = ImageOps.expand(on_white, 2, fill=255).filter(ImageFilter.FIND_EDGES).crop((2, 2, 2 + big.width, 2 + big.height))  # no edge on the border
    inner = inner.point(lambda v: 255 if v > 40 else 0)
    outer = ImageChops.subtract(alpha, alpha.filter(ImageFilter.MinFilter(3)))
    dots = ImageChops.lighter(inner, outer).resize((w, h), Image.BOX).point(lambda v: 255 if v > 0 else 0)
    lines = ["".join(chr(0x2800 + sum(bit for dx, dy, bit in BITS if dots.getpixel((2 * x + dx, 4 * y + dy))))
                     for x in range(w // 2)) for y in range(h // 4)]
    while all(c == "⠀" for c in lines[0]):
        lines.pop(0)
    while all(c == "⠀" for c in lines[-1]):
        lines.pop()
    left = min(len(l) - len(l.lstrip("⠀")) for l in lines)
    right = max(len(l.rstrip("⠀")) for l in lines)
    return "\n".join(l[left:right] for l in lines) + "\n"


def check():
    words = tomllib.loads((Path(__file__).parent / "emoji.toml").read_text())
    colors = tomllib.loads((PICTURES / "colors.toml").read_text())
    problems = []
    for word in words:
        if not (PICTURES / f"{word}.txt").exists():
            problems.append(f"{word}: no picture")
    for path in sorted(PICTURES.glob("*.txt")):
        lines = path.read_text(encoding="utf-8").expandtabs(8).split("\n")[:-1]
        if len(lines) > MAX_ROWS or max(map(len, lines)) > MAX_COLS:
            problems.append(f"{path.name}: {max(map(len, lines))} x {len(lines)}, more than {MAX_COLS} x {MAX_ROWS}")
        if path.stem not in colors:
            problems.append(f"{path.stem}: no color")
    print("\n".join(problems) or "ok")
    sys.exit(bool(problems))


if "--check" in sys.argv:
    check()
words = tomllib.loads((Path(__file__).parent / "emoji.toml").read_text())
colors = tomllib.loads((PICTURES / "colors.toml").read_text())
with tempfile.TemporaryDirectory() as tmp:
    for word, code in words.items():
        if (PICTURES / f"{word}.txt").exists():
            continue
        png = Path(tmp) / f"{code}.png"
        subprocess.run(["curl", "-sfL", "-o", png, URL % code], check=True)
        img = Image.open(png).convert("RGBA")
        (PICTURES / f"{word}.txt").write_text(braille(img, COLS), encoding="utf-8")
        colors[word] = main_color(img)
(PICTURES / "colors.toml").write_text("".join(f'{w} = "{c}"\n' for w, c in sorted(colors.items())))
