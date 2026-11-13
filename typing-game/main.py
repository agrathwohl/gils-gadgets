#!/usr/bin/env python3
"""
Typing with Gil - A simple typing tutor for toddlers
"""

import argparse
import curses
import os
import random
import re
import subprocess
from collections import deque
from pathlib import Path

import pyfiglet

# Paths
BASE_DIR = Path(__file__).parent
ASCII_DIR = BASE_DIR / "assets" / "ascii"
AUDIO_DIR = BASE_DIR / "audio"

# Runtime config (set in main)
VOICES = []
BIG_LETTERS = True


def get_base_word(filename):
    """Extract base word from filename, stripping trailing numbers.

    duck.txt -> duck
    duck2.txt -> duck
    duck123.txt -> duck
    ice-cream.txt -> ice-cream
    """
    stem = filename.stem.lower()
    return re.sub(r'\d+$', '', stem)


def get_letters_to_type(word):
    """Get the letters the child needs to type (no dashes)."""
    return word.replace('-', '')


def format_display_word(word, typed_count):
    """Format word for display, showing typed letters with dashes as spaces.

    word: base word like "ice-cream"
    typed_count: how many letters have been typed
    Returns: display string like "ICE C" if 4 letters typed
    """
    result = []
    letter_index = 0
    for char in word:
        if char == '-':
            result.append(' ')
        else:
            if letter_index < typed_count:
                result.append(char.upper())
            letter_index += 1
    return ''.join(result)


def get_word_list():
    """Get unique words from ASCII art filenames (ignoring variant numbers)."""
    if not ASCII_DIR.exists():
        return []
    words = set()
    for f in ASCII_DIR.glob("*.txt"):
        if f.is_file():
            words.add(get_base_word(f))
    return list(words)


def pick_word(words, recent):
    """Pick a random word, avoiding recently used ones.

    recent: deque of recently used words (max 5)
    """
    available = [w for w in words if w not in recent]
    if not available:
        # Small word pool - just pick random
        available = words
    return random.choice(available)


def play_audio(path):
    """Play audio file via ALSA. Silent fail if missing."""
    if path.exists():
        subprocess.run(
            ["aplay", "-q", str(path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def find_audio_variants(directory, base_name):
    """Find all variants of an audio file (e.g., a.wav, a_higher.wav)."""
    variants = []
    if directory.exists():
        # Match base_name.wav and base_name_*.wav
        for f in directory.glob(f"{base_name}.wav"):
            variants.append(f)
        for f in directory.glob(f"{base_name}_*.wav"):
            variants.append(f)
    return variants


def play_letter(letter, voice):
    """Play the audio for a letter, randomly choosing from available variants."""
    letter_dir = AUDIO_DIR / voice / "letters"
    variants = find_audio_variants(letter_dir, letter.lower())
    if variants:
        play_audio(random.choice(variants))


def play_word(word, voice):
    """Play the audio for the completed word, randomly choosing from available variants."""
    word_dir = AUDIO_DIR / voice / "words"
    variants = find_audio_variants(word_dir, word.lower())
    if variants:
        play_audio(random.choice(variants))


def play_greeting():
    """Play the startup greeting, randomly choosing from available voices and variants."""
    voice = random.choice(VOICES)
    voice_dir = AUDIO_DIR / voice
    variants = find_audio_variants(voice_dir, "greeting")
    if variants:
        play_audio(random.choice(variants))


def load_ascii_art(word):
    """Load ASCII art for a word, randomly selecting from variants.

    Looks for word.txt, word2.txt, word3.txt, etc.
    """
    # Find all variants: word.txt, word2.txt, word3.txt, etc.
    variants = []
    for f in ASCII_DIR.glob("*.txt"):
        if f.is_file() and get_base_word(f) == word.lower():
            variants.append(f)

    if variants:
        chosen = random.choice(variants)
        return chosen.read_text()
    return f"[ {word.upper()} ]"


def draw_centered(win, y, text, attr=0):
    """Draw text centered on the screen."""
    h, w = win.getmaxyx()
    x = max(0, (w - len(text)) // 2)
    if y < h and x < w:
        win.addstr(y, x, text[:w-x], attr)


def draw_big_letter(win, y, letter):
    """Draw a letter as large ASCII art using pyfiglet. Returns number of lines drawn."""
    big = pyfiglet.figlet_format(letter, font="big")
    lines = big.rstrip('\n').split('\n')
    for i, line in enumerate(lines):
        draw_centered(win, y + i, line, curses.A_BOLD)
    return len(lines)


def get_art_char_positions(art):
    """Get list of (line_idx, char_idx) for all non-space characters."""
    positions = []
    lines = art.strip().split('\n')
    for line_idx, line in enumerate(lines):
        for char_idx, char in enumerate(line):
            if char not in ' \t':
                positions.append((line_idx, char_idx))
    return positions


def mask_ascii_art(art, reveal_count):
    """Return ASCII art with only reveal_count characters visible.

    Characters are revealed left-to-right, top-to-bottom.
    """
    lines = art.strip().split('\n')
    positions = get_art_char_positions(art)

    # Which positions should be visible
    visible = set(positions[:reveal_count])

    # Build masked art
    result = []
    for line_idx, line in enumerate(lines):
        masked_line = []
        for char_idx, char in enumerate(line):
            if char in ' \t':
                masked_line.append(char)
            elif (line_idx, char_idx) in visible:
                masked_line.append(char)
            else:
                masked_line.append(' ')
        result.append(''.join(masked_line))

    return '\n'.join(result)


def draw_ascii_art(win, art, start_y):
    """Draw ASCII art centered on screen."""
    h, w = win.getmaxyx()
    lines = art.strip().split('\n')
    for i, line in enumerate(lines):
        y = start_y + i
        if y < h - 1:
            x = max(0, (w - len(line)) // 2)
            try:
                win.addstr(y, x, line[:w-x])
            except curses.error:
                pass


def typing_round(win, word):
    """Run one round of typing a word."""
    h, w = win.getmaxyx()

    # Pick one voice for this entire word
    voice = random.choice(VOICES)

    # Load ASCII art upfront for progressive reveal
    art = load_ascii_art(word)
    art_positions = get_art_char_positions(art)
    total_chars = len(art_positions)

    letters = get_letters_to_type(word)
    total_letters = len(letters)

    # Calculate chars to reveal per letter
    chars_per_letter = total_chars / total_letters if total_letters > 0 else total_chars

    typed_count = 0
    art_start_y = 2
    if BIG_LETTERS:
        typed_y = h - 10
        letter_y = typed_y - 10
    else:
        letter_y = h - 6
        typed_y = h - 4

    for letter in letters:
        win.clear()

        # Show partially revealed ASCII art
        reveal_count = int(typed_count * chars_per_letter)
        masked_art = mask_ascii_art(art, reveal_count)
        draw_ascii_art(win, masked_art, art_start_y)

        # Show the letter to type
        if BIG_LETTERS:
            draw_big_letter(win, letter_y, letter.upper())
        else:
            draw_centered(win, letter_y, letter.upper(), curses.A_BOLD)

        # Show typed progress so far (with spaces for dashes)
        if typed_count > 0:
            progress = format_display_word(word, typed_count)
            if BIG_LETTERS:
                draw_big_letter(win, typed_y, progress)
            else:
                draw_centered(win, typed_y, progress)

        win.refresh()

        # Play letter audio
        play_letter(letter, voice)

        # Wait for correct keypress
        while True:
            key = win.getch()

            # Quit on ESC
            if key == 27:
                return False

            # Check if correct letter (case insensitive)
            if key == ord(letter.lower()) or key == ord(letter.upper()):
                typed_count += 1

                # Show updated progress with more art revealed
                win.clear()
                reveal_count = int(typed_count * chars_per_letter)
                masked_art = mask_ascii_art(art, reveal_count)
                draw_ascii_art(win, masked_art, art_start_y)

                if typed_count > 0:
                    progress = format_display_word(word, typed_count)
                    if BIG_LETTERS:
                        draw_big_letter(win, typed_y, progress)
                    else:
                        draw_centered(win, typed_y, progress)
                win.refresh()
                curses.napms(400)

                break
            # Wrong key - just ignore

    # Word complete - show full ASCII art
    win.clear()

    # Show completed word (dashes become spaces)
    display_word = word.replace('-', ' ').upper()
    if BIG_LETTERS:
        draw_big_letter(win, typed_y, display_word)
    else:
        draw_centered(win, typed_y, display_word, curses.A_BOLD)

    # Show full art
    draw_ascii_art(win, art, art_start_y)

    win.refresh()

    # Play the completed word
    play_word(word, voice)

    # Pause to admire the art, then continue
    curses.napms(3000)

    # Clear any buffered input
    win.nodelay(True)
    while win.getch() != -1:
        pass
    win.nodelay(False)

    return True


def run_game(stdscr):
    """Run the typing game."""
    # Setup curses
    curses.curs_set(0)  # Hide cursor
    stdscr.clear()
    stdscr.refresh()

    # Play greeting
    play_greeting()

    # Get word list
    words = get_word_list()

    if not words:
        stdscr.addstr(0, 0, "No words found! Add .txt files to assets/ascii/")
        stdscr.addstr(1, 0, "Press any key to exit...")
        stdscr.refresh()
        stdscr.getch()
        return

    # Track recent words to avoid repetition
    recent = deque(maxlen=5)

    # Main loop
    while True:
        word = pick_word(words, recent)
        recent.append(word)
        if not typing_round(stdscr, word):
            break

    # Goodbye
    stdscr.clear()
    draw_centered(stdscr, stdscr.getmaxyx()[0] // 2, "Bye bye!")
    stdscr.refresh()
    curses.napms(1000)


def detect_voices():
    """Detect which voices have audio files available."""
    available = []
    for voice in ["dad", "mom"]:
        letters_dir = AUDIO_DIR / voice / "letters"
        if letters_dir.exists() and any(letters_dir.glob("*.wav")):
            available.append(voice)
    return available if available else ["dad"]  # fallback


def main():
    global VOICES, BIG_LETTERS

    parser = argparse.ArgumentParser(description="Typing with Gil")
    parser.add_argument("--voice", choices=["dad", "mom", "both"], default="both",
                        help="Which voice to use (default: both)")
    parser.add_argument("--small-letters", action="store_true",
                        help="Use small single-character letters instead of big figlet ones")
    args = parser.parse_args()

    if args.small_letters:
        BIG_LETTERS = False

    if args.voice == "both":
        VOICES = detect_voices()
    else:
        VOICES = [args.voice]

    print(f"Using voice(s): {', '.join(VOICES)}")

    # Create directories if needed
    ASCII_DIR.mkdir(parents=True, exist_ok=True)

    curses.wrapper(run_game)


if __name__ == "__main__":
    main()
