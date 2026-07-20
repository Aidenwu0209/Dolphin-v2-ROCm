"""Micro-profile: prefill/decode token rates for Dolphin-v2 on the current GPU.

Separates image preprocessing, prefill, and decode so that optimization work
targets the real bottleneck. Run inside the model environment:

    python scripts/profile_decode.py --model /root/workspace/models/Dolphin-v2 \
        --image /root/workspace/samples/page_1.png
"""

from __future__ import annotations

import argparse
import json
import time

import torch
from PIL import Image
from qwen_vl_utils import process_vision_info
from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration


def profile_once(model, proc, prompt: str, image: Image.Image, max_new: int) -> dict:
    msgs = [
        {
            "role": "user",
            "content": [{"type": "image", "image": image}, {"type": "text", "text": prompt}],
        }
    ]
    text = proc.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    imgs, _ = process_vision_info(msgs)

    t0 = time.perf_counter()
    inputs = proc(text=[text], images=imgs, return_tensors="pt", padding=True)
    preproc_s = time.perf_counter() - t0
    inputs = inputs.to(model.device)
    n_in = inputs.input_ids.shape[1]

    # prefill-only timing: generate exactly 1 token
    torch.cuda.synchronize()
    t1 = time.perf_counter()
    with torch.inference_mode():
        model.generate(**inputs, max_new_tokens=1, do_sample=False, temperature=None)
    torch.cuda.synchronize()
    prefill_s = time.perf_counter() - t1

    torch.cuda.synchronize()
    t2 = time.perf_counter()
    with torch.inference_mode():
        out = model.generate(**inputs, max_new_tokens=max_new, do_sample=False, temperature=None)
    torch.cuda.synchronize()
    total_s = time.perf_counter() - t2
    n_out = out.shape[1] - n_in
    decode_s = max(total_s - prefill_s, 1e-6)
    return {
        "prompt": prompt[:40],
        "image_size": list(image.size),
        "preproc_s": round(preproc_s, 3),
        "input_tokens": int(n_in),
        "output_tokens": int(n_out),
        "prefill_s": round(prefill_s, 3),
        "generate_s": round(total_s, 3),
        "decode_tok_per_s": round(n_out / decode_s, 1),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--attn", default="sdpa")
    parser.add_argument("--max-new", type=int, default=512)
    args = parser.parse_args()

    proc = AutoProcessor.from_pretrained(args.model)
    model = (
        Qwen2_5_VLForConditionalGeneration.from_pretrained(
            args.model, torch_dtype=torch.bfloat16, attn_implementation=args.attn
        )
        .eval()
        .to("cuda")
    )
    proc.tokenizer.padding_side = "left"
    image = Image.open(args.image).convert("RGB")

    results = []
    # warmup
    profile_once(model, proc, "Read text in the image.", image.crop((0, 0, 400, 200)), 32)
    results.append(profile_once(model, proc, "Parse the reading order of this document.", image, args.max_new))
    results.append(profile_once(model, proc, "Read text in the image.", image.crop((100, 300, 900, 700)), args.max_new))
    results.append(profile_once(model, proc, "Read text in the image.", image, args.max_new))
    print(json.dumps({"attn": args.attn, "results": results}, indent=2))


if __name__ == "__main__":
    main()
