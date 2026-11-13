# Customize

Make the gadgets your child's own: their favorite things as words and pictures, and your voice saying the letters. Everything is a plain file in a folder. You change the files, build a new image, and write it to the SD card.

## The typing game

The typing game has one word for each picture file, and it plays sound files for the letters and the words:

```
typing-game/
├── assets/ascii/
│   ├── truck.txt          picture for TRUCK (the file name is the word)
│   ├── cat.txt            picture for CAT
│   └── cat2.txt           another picture for CAT (one of them is picked at random)
└── audio/
    ├── dad/
    │   ├── greeting.wav   plays when the game starts
    │   ├── letters/a.wav  the letter A (a_higher.wav, a_2.wav, ... are other ways to say it)
    │   └── words/truck.wav the word TRUCK
    └── mom/               the same for a second voice
```

- Use lowercase file names. For two words, use a dash: `ice-cream.txt` gives ICE CREAM, and its sound is `words/ice-cream.wav`.
- The voice folders must have the names `dad` and `mom`. You can have one or both.
- A word or letter without a sound file is silent. Nothing breaks.

### Example: add "cube" and remove "robot"

Your child loves blocks and is bored of the robot. In this example, you add the word CUBE with a picture and your voice, and you remove ROBOT. All commands run in the `typing-game` folder:

```sh
cd gils-gadgets/typing-game
```

**1. Remove "robot".** Delete its picture and its word sound, if there is one:

```sh
rm assets/ascii/robot.txt
rm -f audio/*/words/robot*.wav
```

**2. Make a picture for "cube".** You have two choices.

*Find a picture.* The [ASCII Art Archive](https://www.asciiart.eu/) has thousands of pictures. Copy one into `assets/ascii/cube.txt`. Keep the artist's initials in the picture, if it has them.

*Or make one from a photo or a drawing.* Draw a cube on paper, take a photo, and save it as `cube.png`. Then convert it with [ascii-image-converter](https://github.com/TheZoraiz/ascii-image-converter):

```sh
nix-shell -p ascii-image-converter --run \
  'ascii-image-converter cube.png --braille --negative --width 50' > assets/ascii/cube.txt
```

- `--braille` draws with small dots. Many pictures in the game use this style.
- `--negative` makes dark lines on white paper into bright dots on the black screen.
- `--width 50` makes the picture 50 characters wide. Look at the other pictures for a good size. The picture must fit above the big letters.

Look at the result (here without its empty lines):

```sh
cat assets/ascii/cube.txt
```

```
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣀⣠⣤⣠⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣴⠟⠉⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣡⣿⡿⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⡴⠋⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣴⣿⡿⠋⠀⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣠⡾⠋⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⣴⣿⠟⠁⠀⠀⠀⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢰⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠟⠁⠀⠀⠀⠀⠀⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⡇⠀⠀⠀⠀⠀⠀⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⡇⠀⠀⠀⠀⠀⠀⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⡇⠀⠀⠀⠀⠀⠀⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⡇⠀⠀⠀⠀⠀⠀⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⡇⠀⠀⠀⠀⠀⠀⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⡇⠀⠀⠀⢀⣠⠞⠋⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⡇⠀⢀⣴⠟⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⡇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⣥⡶⠋⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠸⠷⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠾⠟⠋⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
```

**3. Say "cube".** Record your voice for 2 seconds. Start the `arecord` command, then say "cube":

```sh
mkdir -p audio/dad/words
arecord -f S16_LE -r 24000 -c 1 -d 2 audio/dad/words/cube.wav
aplay audio/dad/words/cube.wav
```

If you do not like it, record it again. For the second voice, record `audio/mom/words/cube.wav` the same way. If you made your voices with a computer (see [below](#option-b-copy-a-voice-with-a-computer)), run `generate_words.py` instead. It makes only the words that do not have a sound yet.

**4. Try it on your computer** (optional):

```sh
uv run --with pyfiglet python main.py
```

The game picks words at random, so CUBE can take a few rounds to come. Press **Esc** to stop.

**5. Put it on the SD card.** Go back to the top folder, build, and write the card ([build guide](BUILD.md), steps 8 and 9):

```sh
cd ..
./build.sh
```

Done. The next time your child plays, ROBOT is gone and CUBE is there, in your voice.

### Record the letters

Record all 26 letters in one go, in bash. For each letter, press Enter and then say the letter:

```sh
mkdir -p audio/dad/letters
for l in {a..z}; do
  read -p "Press Enter, then say: $l"
  arecord -f S16_LE -r 24000 -c 1 -d 2 audio/dad/letters/$l.wav
done
```

To have more than one way to say a letter, add files with an underscore, for example `audio/dad/letters/a_happy.wav`. The game picks one at random.

### The greeting

`audio/dad/greeting.wav` plays when the game starts. For example, record "Hi! Let's type!":

```sh
arecord -f S16_LE -r 24000 -c 1 -d 3 audio/dad/greeting.wav
```

### Option A: record your own voice

This is what the steps above do. You need a microphone and `arecord` (from alsa-utils). Any other recorder works too, if it saves WAV files.

### Option B: copy a voice with a computer

Gil's voices came from the scripts in `typing-game/scripts/`. They use the [Qwen3-TTS](https://pypi.org/project/qwen-tts/) speech model to copy a voice from one recording, and then make every letter, word and greeting in that voice. You need an NVIDIA graphics card.

1. Record 30 to 60 seconds of normal speech from the parent. Save it as `audio/voice_reference_dad.wav` (or `voice_reference_mom.wav`):

   ```sh
   mkdir -p audio
   arecord -f S16_LE -r 48000 -c 1 -d 30 audio/voice_reference_dad.wav
   ```

2. Put your child's name in the greeting. In `scripts/generate_greeting.py`, change this line:

   ```python
   GREETING = "Hi Gil! Let's type."
   ```

3. Make the sounds:

   ```sh
   uv run --with qwen-tts python scripts/generate_letters.py --voice dad
   uv run --with qwen-tts python scripts/generate_words.py --voice dad
   uv run --with qwen-tts python scripts/generate_greeting.py --voice dad
   ```

   Add `--higher-inflection` to make a second, happier set (`a_higher.wav`, ...). The scripts skip the files that already exist, so you can run them again after you add a word.

## The musical keyboard

### Change a picture

Each instrument has a picture in `musical-keyboard/assets/ascii/`. The file name is the instrument name, with dashes for spaces: `double-bass.txt`, `drum-kit-1.txt`. Replace the file to change the picture. Make new pictures the same way as for the typing game.

### Add or remove an instrument

The instruments are a list near the top of `musical-keyboard/app.py`:

```python
INSTRUMENTS = [
    ("violin", 0, 40),
    ("double bass", 0, 43),
    ...
]
```

Each line has a name, a bank and a program:

- **Bank 0** is a normal instrument. Its program is the [General MIDI](https://en.wikipedia.org/wiki/General_MIDI#Program_change_events) instrument number **minus 1**. Example: General MIDI 74 is Flute, so the flute is `("flute", 0, 73)`.
- **Bank 128** is a drum kit. Its program is the kit number in the soundfont.

**Example: add a flute.**

1. Add a line to the list, where you want it in the order: `("flute", 0, 73),`
2. Add a picture: `musical-keyboard/assets/ascii/flute.txt`.
3. Build and write the card.

To remove an instrument, delete its line and its picture. Keep the line for `drum kit 1`, because the pads use that kit while a normal instrument is on the screen.

To try your change on your computer, see [Run it on your computer](musical-keyboard/README.md#run-it-on-your-computer).

## After every change

```sh
./build.sh
```

Then write the new image to the SD card ([build guide](BUILD.md), step 9).
