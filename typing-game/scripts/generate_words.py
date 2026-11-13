#!/usr/bin/env python3
"""
Generate word audio files using Qwen3-TTS voice cloning.
Words are derived from ASCII art filenames (deduplicated).

Usage:
    conda activate qwen3-tts
    python scripts/generate_words.py --voice dad
    python scripts/generate_words.py --voice mom
    python scripts/generate_words.py --voice dad --higher-inflection
"""

import argparse
import re
import torch
import numpy as np
import soundfile as sf
from pathlib import Path
from qwen_tts import Qwen3TTSModel

# Paths
BASE_DIR = Path(__file__).parent.parent
ASCII_DIR = BASE_DIR / "assets" / "ascii"

# Instruction for higher inflection
HIGHER_INFLECTION_INSTRUCT = "Single word. Upbeat, happy."


def get_base_word(filename):
    """Extract base word from filename, stripping trailing numbers."""
    stem = filename.stem.lower()
    return re.sub(r'\d+$', '', stem)


def get_word_list():
    """Get unique words from ASCII art filenames."""
    if not ASCII_DIR.exists():
        return []
    words = set()
    for f in ASCII_DIR.glob("*.txt"):
        if f.is_file():
            word = get_base_word(f)
            if word:
                words.add(word)
    return sorted(words)


def generate_with_instruct(model, text, language, voice_clone_prompt, instruct=None):
    """Generate audio with voice cloning AND optional instruction for emotion/style."""
    device = next(model.model.parameters()).device

    # Build input text
    assistant_text = f"<|im_start|>assistant\n{text}<|im_end|>\n"
    input_ids = model.processor(text=assistant_text, return_tensors="pt", padding=True)["input_ids"].to(device)

    # Build instruct_ids if instruction provided
    instruct_ids = None
    if instruct:
        instruct_text = f"<|im_start|>user\n{instruct}<|im_end|>\n"
        instruct_ids = [model.processor(text=instruct_text, return_tensors="pt", padding=True)["input_ids"].to(device)]

    # Convert prompt items to dict format
    prompt_dict = model._prompt_items_to_voice_clone_prompt(voice_clone_prompt)

    # Generate using low-level API
    gen_kwargs = dict(
        max_new_tokens=2048,
        do_sample=True,
        top_k=50,
        top_p=1.0,
        temperature=0.9,
        repetition_penalty=1.05,
    )

    talker_codes_list, _ = model.model.generate(
        input_ids=[input_ids],
        instruct_ids=instruct_ids,
        ref_ids=[None],
        voice_clone_prompt=prompt_dict,
        languages=[language],
        non_streaming_mode=False,
        **gen_kwargs,
    )

    # Decode audio
    codes_for_decode = []
    for i, codes in enumerate(talker_codes_list):
        ref_code_list = prompt_dict.get("ref_code", None)
        if ref_code_list is not None and ref_code_list[i] is not None:
            codes_for_decode.append(torch.cat([ref_code_list[i].to(codes.device), codes], dim=0))
        else:
            codes_for_decode.append(codes)

    wavs_all, fs = model.model.speech_tokenizer.decode([{"audio_codes": c} for c in codes_for_decode])

    # Trim reference audio portion
    wavs_out = []
    for i, wav in enumerate(wavs_all):
        ref_code_list = prompt_dict.get("ref_code", None)
        if ref_code_list is not None and ref_code_list[i] is not None:
            ref_len = int(ref_code_list[i].shape[0])
            total_len = int(codes_for_decode[i].shape[0])
            cut = int(ref_len / max(total_len, 1) * wav.shape[0])
            wavs_out.append(wav[cut:])
        else:
            wavs_out.append(wav)

    return wavs_out, fs


def main():
    parser = argparse.ArgumentParser(description="Generate word audio")
    parser.add_argument("--voice", choices=["dad", "mom"], default="dad",
                        help="Which voice to use (default: dad)")
    parser.add_argument("--higher-inflection", action="store_true",
                        help="Generate with upbeat, positive inflection")
    args = parser.parse_args()

    voice_ref = BASE_DIR / "audio" / f"voice_reference_{args.voice}.wav"
    output_dir = BASE_DIR / "audio" / args.voice / "words"
    output_dir.mkdir(parents=True, exist_ok=True)

    suffix = "_higher" if args.higher_inflection else ""
    instruct = HIGHER_INFLECTION_INSTRUCT if args.higher_inflection else None

    words = get_word_list()
    if not words:
        print(f"No ASCII art files found in {ASCII_DIR}")
        return

    print(f"Voice: {args.voice}")
    print(f"Inflection: {'higher/upbeat' if args.higher_inflection else 'normal'}")
    print(f"Found {len(words)} unique words: {', '.join(words)}")

    print("\nLoading Qwen3-TTS model...")
    model = Qwen3TTSModel.from_pretrained(
        "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
        device_map="cuda:0",
        dtype=torch.bfloat16,
    )

    print(f"Creating voice clone prompt from: {voice_ref}")
    prompt = model.create_voice_clone_prompt(
        ref_audio=str(voice_ref),
        x_vector_only_mode=True,
    )

    print("\nGenerating word audio...")
    generated = 0
    skipped = 0

    for word in words:
        output_path = output_dir / f"{word}{suffix}.wav"

        if output_path.exists():
            print(f"  {word}{suffix}.wav (skipped - exists)", flush=True)
            skipped += 1
            continue

        # Convert dashes to spaces for speech
        spoken_word = word.replace('-', ' ')

        if instruct:
            wavs, sr = generate_with_instruct(model, spoken_word, "English", prompt, instruct)
        else:
            wavs, sr = model.generate_voice_clone(
                text=spoken_word,
                language="English",
                voice_clone_prompt=prompt,
            )

        sf.write(str(output_path), wavs[0], sr)
        print(f"  {word}{suffix}.wav", flush=True)
        generated += 1

    print(f"\nDone! Generated {generated}, skipped {skipped} (already exist)")


if __name__ == "__main__":
    main()
