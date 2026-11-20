#!/usr/bin/env python3
"""
Make Clips - adult test clips for listen.py --test, spoken by Piper voices

    nix-shell -p piper-tts ffmpeg fluidsynth --run 'uv run python story/scripts/make_clips.py VOICES OUT BOOK...'

VOICES is a folder with Piper voices (<voice>.onnx and <voice>.onnx.json from
https://huggingface.co/rhasspy/piper-voices). BOOK is a children's text without the word "story" (for example a
Beatrix Potter book from Project Gutenberg). OUT gets wake/, sentences/, near/, overlap/ and false/: each clip is
<name>.wav with the words said in <name>.txt. The false wake clips use the family voices of the typing game, so keep
OUT out of the repo.
"""

import json
import re
import struct
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SILENCE = bytes(16000)  # 0.5 s, before and after each clip

WAKE = [
    "story", "Story!", "story please", "tell me a story", "story time", "I want a story", "a story about a dog",
    "story, story", "let's make a story", "can we do a story?", "story now please", "the story", "my story",
    "one more story", "Story?", "make a story", "a silly story", "story please mommy", "I like the story",
    "it's story time",
]

SENTENCES = [
    "the dog jumps up", "the big cat eats the banana", "mommy hugs the baby", "the red car goes fast",
    "the elephant sleeps", "the duck swims", "the frog jumps down", "the bee flies up", "the tiger runs fast",
    "the cow eats the apple", "the train goes in the house", "the snake hides", "the bunny dances",
    "the owl sees the moon", "the robot sings", "the bear hugs the panda", "the turtle goes slow",
    "the penguin falls down", "the helicopter flies", "the horse runs", "the small dog plays with the cat",
    "the blue boat goes", "the spider comes out", "the happy cow sings", "the airplane flies up",
    "the snail goes in the house", "the silly monkey jumps", "the green frog eats the strawberry",
    "the dolphin swims fast", "the truck goes down", "the yellow duck shares the apple", "the baby sleeps",
    "the chicken runs", "the lion helps the mouse", "the purple elephant dances", "the cat in the hat jumped",
    "the doggy ate the cake", "the kitty is sad", "the pink pig is happy", "humpty dumpty fell down",
]

# Words near "story", without it: false wakes
NEAR = [
    "the star jumps", "I am sorry", "we go to the store", "it is a stormy day", "a starry night", "I like history",
    "the big star sleeps", "sorry mommy", "the store is big", "twinkle twinkle little star", "the stars come out",
    "a stormy sky", "look at the starry sky", "history is fun", "I'm sorry, doggy", "the store has cake",
    "the star and the moon", "sorry, sorry", "the stormy sea", "the yellow star flies up",
]

# Names of many words whose parts are names too: each must come out as one phrase
OVERLAP = [
    "the teddy bear jumps", "the cat in the hat eats the ice cream", "the fire truck goes fast", "the polar bear swims",
    "the police car goes", "the race car runs fast", "the baby bottle falls down", "the palm tree is big",
    "the crystal ball is pink", "the grand piano sings", "the T-Rex eats the french fries",
    "humpty dumpty sees the roller coaster", "the drum kit plays", "the light bulb is hot", "the magic wand flies",
    "the yo-yo goes up and down",
]


def pcm(path):
    """The audio of a file as mono 16-bit 16 kHz samples."""
    return subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(path), "-f", "s16le", "-ac", "1", "-ar", "16000",
                           "-"], capture_output=True, check=True).stdout


def say(text, voice):
    model, speaker = voice
    with tempfile.NamedTemporaryFile(suffix=".wav") as f:
        subprocess.run(["piper", "-m", str(model), "-s", str(speaker), "-f", f.name], input=text.encode(),
                       capture_output=True, check=True)
        return pcm(f.name)


def save(path, audio, words):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(SILENCE + audio + SILENCE)
    path.with_suffix(".txt").write_text(words + "\n")
    print(path)


def tune():
    """Twinkle Twinkle on the piano with chords, as a MIDI file: 64 beats at 120 bpm."""
    events = bytearray()
    for i, note in enumerate([60, 60, 67, 67, 69, 69, 67, 67, 65, 65, 64, 64, 62, 62, 60, 60] * 4):
        notes = [note] + ([note - 12, note - 8, note - 5] if i % 2 == 0 else [])
        for key in notes:
            events += bytes([0, 0x90, key, 90])
        for j, key in enumerate(notes):
            events += (b"\x83\x60" if j == 0 else b"\x00") + bytes([0x80, key, 0])  # note off after 480 ticks
    events += b"\x00\xff\x2f\x00"
    return b"MThd" + struct.pack(">IHHH", 6, 0, 1, 480) + b"MTrk" + struct.pack(">I", len(events)) + events


def main():
    voices_dir, out, books = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3:]
    voices = []  # (model, speaker): up to 5 speakers of a voice with many
    for model in sorted(voices_dir.glob("*.onnx")):
        speakers = json.loads(Path(f"{model}.json").read_text())["num_speakers"]
        voices += [(model, s) for s in range(0, speakers, max(1, speakers // 5))][:5]

    clips = {"wake": WAKE, "sentences": SENTENCES, "near": NEAR, "overlap": OVERLAP}
    for n, (folder, texts) in enumerate(clips.items()):
        for i, text in enumerate(texts):
            save(out / folder / f"{i:02}.wav", say(text, voices[(i + 3 * n) % len(voices)]), text)

    text = "".join(re.search(r"\*\*\* START OF.*?\*\*\*(.*)\*\*\* END OF", Path(book).read_text(), re.S)[1]
                   for book in books)
    paragraphs = [" ".join(p.split()) for p in re.split(r"\n\s*\n", re.sub(r"\[Illustration[^]]*\]", "", text))]
    paragraphs = [p for p in paragraphs if p and not re.search(r"\bstor(y|ies)\b", p, re.I)]
    save(out / "false" / "book.wav", b"".join(say(p, voices[i % len(voices)]) + SILENCE
                                              for i, p in enumerate(paragraphs)), "\n".join(paragraphs))

    family = sorted((ROOT / "typing-game" / "audio").rglob("*.wav"))
    save(out / "false" / "family.wav", b"".join(pcm(f) + SILENCE for f in family),
         " ".join(f.stem.replace("-", " ") for f in family if "voice_reference" not in f.stem))

    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "tune.mid").write_bytes(tune())
        subprocess.run(["fluidsynth", "-ni", "-q", "-r", "16000", "-F", f"{tmp}/piano.wav",
                        str(next(ROOT.glob("musical-keyboard/*.sf2"))), f"{tmp}/tune.mid"],
                       capture_output=True, check=True)
        save(out / "false" / "piano.wav", pcm(f"{tmp}/piano.wav"), "")


if __name__ == "__main__":
    main()
