#!/usr/bin/env python3
"""
Listen - hears the wake word "story", then the words of the story, offline (sherpa-onnx)
"""

import argparse
import array
import collections
import io
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import sentencepiece
import sherpa_onnx

MODELS = Path(__file__).parent / "models"
RATE = 16000
SENTENCE_END = 1.5  # seconds after the last new known phrase (a TV in the room is never quiet), or of quiet
STORY = ":0.5 #0.15"  # the boost and threshold of "story", tuned on the test clips (scripts/make_clips.py)
# Words near "story". The spotter finds them, and so does not take them for "story".
NOT_STORY = ["store", "storm", "stormy", "star", "stars", "starry", "sorry", "history"]
HOTWORDS = 3.0  # how much the recognizer prefers the phrases


def models(phrases):
    """The keyword spotter for "story", and the speech recognizer with the phrases as hotwords."""
    kws, asr = MODELS / "kws", MODELS / "asr"
    bpe = sentencepiece.SentencePieceProcessor(model_file=str(kws / "bpe.model"))
    asr_bpe = sentencepiece.SentencePieceProcessor(model_file=str(asr / "bpe.model"))

    def pieces(word):
        return " ".join(bpe.encode(word.upper(), out_type=str))

    with (tempfile.NamedTemporaryFile("w") as keywords, tempfile.NamedTemporaryFile("w") as hotwords,
          tempfile.NamedTemporaryFile("w") as vocab):
        keywords.write("\n".join([f"{pieces('story')} @story {STORY}"] + [f"{pieces(w)} @{w}" for w in NOT_STORY]))
        hotwords.write("\n".join(p.upper() for p in phrases))
        vocab.write("".join(f"{asr_bpe.id_to_piece(i)}\t{asr_bpe.get_score(i)}\n"
                            for i in range(asr_bpe.get_piece_size())))
        for f in (keywords, hotwords, vocab):
            f.flush()
        spotter = sherpa_onnx.KeywordSpotter(
            tokens=str(kws / "tokens.txt"),
            encoder=str(kws / "encoder-epoch-12-avg-2-chunk-16-left-64.int8.onnx"),
            decoder=str(kws / "decoder-epoch-12-avg-2-chunk-16-left-64.int8.onnx"),
            joiner=str(kws / "joiner-epoch-12-avg-2-chunk-16-left-64.int8.onnx"),
            keywords_file=keywords.name, num_threads=1)
        recognizer = sherpa_onnx.OnlineRecognizer.from_transducer(
            tokens=str(asr / "tokens.txt"),
            encoder=str(asr / "encoder-epoch-99-avg-1.int8.onnx"),
            decoder=str(asr / "decoder-epoch-99-avg-1.int8.onnx"),
            joiner=str(asr / "joiner-epoch-99-avg-1.int8.onnx"),
            num_threads=1, decoding_method="modified_beam_search", hotwords_file=hotwords.name,
            hotwords_score=HOTWORDS, bpe_vocab=vocab.name, modeling_unit="bpe",
            enable_endpoint_detection=True, rule2_min_trailing_silence=SENTENCE_END)
    return spotter, recognizer


def known(words, phrases):
    """The phrases in a list of words, the longest first, in order."""
    longest = max(len(p.split()) for p in phrases)
    found, i = [], 0
    while i < len(words):
        n = next((n for n in range(longest, 0, -1) if " ".join(words[i:i + n]) in phrases), 0)
        if n:
            found.append(" ".join(words[i:i + n]))
        i += n or 1
    return found


def spot(spotter, recognizer, phrases, awake, pcm):
    """Yields "story" or the sentences heard in raw audio (mono, 16-bit, 16 kHz) read from pcm, until it ends."""
    is_awake, sentence, n, last = None, [], 0, 0
    while True:
        data = pcm.read(RATE // 5)  # 0.1 s
        if awake.is_set() != is_awake:
            # Asleep only the small keyword spotter runs, awake only the recognizer
            is_awake = awake.is_set()
            model = recognizer if is_awake else spotter
            stream = model.create_stream()
            if is_awake:
                stream.accept_waveform(RATE, [0.0] * RATE)  # a new recognizer stream misses its first second or so
            sentence = []
        if data:
            stream.accept_waveform(RATE, [x / 32768 for x in array.array("h", data)])
            n += len(data) // 2
        else:
            stream.accept_waveform(RATE, [0.0] * RATE)  # so that the last word is decoded
            stream.input_finished()
        while model.is_ready(stream):
            model.decode_stream(stream)
            # A keyword shows in the result of the one decode that found it. No reset_stream(): it would also
            # reset the encoder, which then hears the next words without what came before.
            if not is_awake and spotter.get_result(stream) == "story":
                yield "story"
        if is_awake:
            heard = known(re.findall(r"[a-z']+", recognizer.get_result(stream).lower()), phrases)
            if heard != sentence:
                sentence, last = heard, n
            if recognizer.is_endpoint(stream) or (sentence and (not data or n - last >= SENTENCE_END * RATE)):
                if sentence:
                    yield sentence
                recognizer.reset(stream)
                sentence = []
        if not data:
            return


def microphone():
    """The ALSA device in STORY_MIC, else the first capture device on a card with "USB" in its name,
    else the first capture device, or None."""
    if os.environ.get("STORY_MIC"):
        return os.environ["STORY_MIC"]
    pcm = Path("/proc/asound/pcm")
    devices = re.findall(r"^(\d+)-(\d+):.*: capture", pcm.read_text() if pcm.exists() else "", re.M)
    if not devices:
        return None
    cards = {int(n): (card, name) for n, card, name in
             re.findall(r"^ *(\d+) \[(\S+) *\]: (.*)", Path("/proc/asound/cards").read_text(), re.M)}
    card, device = min(devices, key=lambda d: "USB" not in cards[int(d[0])][1])  # min keeps the first of equals
    return f"plughw:CARD={cards[int(card)][0]},DEV={int(device)}"


def decode(file, *options):
    return ["ffmpeg", "-nostdin", "-loglevel", "error", *options, "-i", str(file),
            "-f", "s16le", "-ac", "1", "-ar", str(RATE), "-"]


def listen(phrases, awake, file=None):
    """Yields "story" while awake is not set, else a list of the known phrases of each sentence, in order.
    It listens to the microphone, or plays a file in real time."""
    spotter, recognizer = models(phrases)
    phrases = set(phrases)
    while True:
        device = None if file else microphone()
        if file or device:
            command = decode(file, "-re") if file else [
                "arecord", "-q", "-D", device, "-f", "S16_LE", "-r", str(RATE), "-c", "1", "-t", "raw"]
            # Nothing on the console: the story's console is hidden, and the screen saver counts writes
            with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL) as p:
                yield from spot(spotter, recognizer, phrases, awake, p.stdout)
            if file:
                return
        time.sleep(5)  # no microphone, or a child pulled it out: look again


def test(folder, phrases):
    """Scores the clips <name>.<any ffmpeg format> in folder, with the words said in <name>.txt:
    "story" is spotted while asleep, and the known words while awake from the start."""
    spotter, recognizer = models(phrases)
    phrases = set(phrases)
    clips = wakes = false_wakes = quiet = expected = found = heard = 0
    for label in sorted(Path(folder).glob("*.txt")):
        clip = next((p for p in label.parent.glob(label.stem + ".*") if p.suffix != ".txt"), None)
        if not clip:
            sys.exit(f"{label}: there is no recording with this name")
        audio = subprocess.run(decode(clip), capture_output=True, check=True).stdout
        said = re.findall(r"[a-z']+", label.read_text().lower())
        asleep, awake = threading.Event(), threading.Event()
        awake.set()
        story = len(list(spot(spotter, recognizer, phrases, asleep, io.BytesIO(audio))))
        words = collections.Counter(w for s in spot(spotter, recognizer, phrases, awake, io.BytesIO(audio)) for w in s)
        wanted = collections.Counter(known(said, phrases))
        if "story" in said:
            clips += 1
            wakes += story > 0
        else:
            false_wakes += story
            quiet += len(audio) / 2 / RATE
        expected += wanted.total()
        found += (wanted & words).total()
        heard += words.total()
        print(f"{clip.name}: story {story}, missed {sorted((wanted - words).elements())}, "
              f"wrong {sorted((words - wanted).elements())}")
    print(f'"story" found in {wakes} of {clips} clips with it; '
          f'{false_wakes} false wakes in {quiet / 60:.1f} minutes without it')
    print(f"known words: {found} of {expected} found ({found / max(expected, 1):.0%}), "
          f"{heard - found} wrong of {heard} heard ({(heard - found) / max(heard, 1):.0%})")


def main():
    parser = argparse.ArgumentParser(description="Listen: print what the story hears")
    parser.add_argument("--phrases", help="a file with one phrase per line (default: the phrases of story.py)")
    parser.add_argument("--file", help="listen to this audio file instead of the microphone; "
                                       "it wakes on \"story\" and stays awake")
    parser.add_argument("--test", metavar="FOLDER", help="score the clips <name>.<format> in FOLDER, "
                                                         "with the words said in <name>.txt")
    args = parser.parse_args()

    if args.phrases:
        phrases = [line.strip().lower() for line in open(args.phrases) if line.strip()]
    else:
        from story import phrases
        phrases = phrases()
    if args.test:
        return test(args.test, phrases)
    awake = threading.Event()
    for heard in listen(phrases, awake, args.file):
        print(heard, flush=True)
        if heard == "story":
            awake.set()


if __name__ == "__main__":
    main()
