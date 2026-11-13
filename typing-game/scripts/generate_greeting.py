#!/usr/bin/env python3
"""
Generate greeting audio using Qwen3-TTS voice cloning.

Usage:
    conda activate qwen3-tts
    python scripts/generate_greeting.py --voice dad
    python scripts/generate_greeting.py --voice mom
    python scripts/generate_greeting.py --voice dad --higher-inflection
"""

import argparse
import torch
import numpy as np
import soundfile as sf
from pathlib import Path
from qwen_tts import Qwen3TTSModel

# Paths
BASE_DIR = Path(__file__).parent.parent

# Greeting text
GREETING = "Hi Gil! Let's type."

# Instruction for higher inflection
HIGHER_INFLECTION_INSTRUCT = "Short greeting. Upbeat, happy."


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
    parser = argparse.ArgumentParser(description="Generate greeting audio")
    parser.add_argument("--voice", choices=["dad", "mom"], default="dad",
                        help="Which voice to use (default: dad)")
    parser.add_argument("--higher-inflection", action="store_true",
                        help="Generate with upbeat, positive inflection")
    args = parser.parse_args()

    voice_ref = BASE_DIR / "audio" / f"voice_reference_{args.voice}.wav"
    output_dir = BASE_DIR / "audio" / args.voice
    output_dir.mkdir(parents=True, exist_ok=True)

    suffix = "_higher" if args.higher_inflection else ""
    instruct = HIGHER_INFLECTION_INSTRUCT if args.higher_inflection else None
    output_file = output_dir / f"greeting{suffix}.wav"

    if output_file.exists():
        print(f"Greeting already exists at {output_file}, skipping.")
        return

    print(f"Voice: {args.voice}")
    print(f"Inflection: {'higher/upbeat' if args.higher_inflection else 'normal'}")
    print("Loading Qwen3-TTS model...")
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

    print(f"Generating greeting: \"{GREETING}\"")
    if instruct:
        wavs, sr = generate_with_instruct(model, GREETING, "English", prompt, instruct)
    else:
        wavs, sr = model.generate_voice_clone(
            text=GREETING,
            language="English",
            voice_clone_prompt=prompt,
        )

    sf.write(str(output_file), wavs[0], sr)
    print(f"Done! Saved to {output_file}")


if __name__ == "__main__":
    main()
