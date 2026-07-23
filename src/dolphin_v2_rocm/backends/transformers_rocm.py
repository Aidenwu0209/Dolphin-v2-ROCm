"""Transformers backend for Dolphin-v2 on ROCm.

This backend stays as close as possible to the upstream Dolphin demo pipeline
(https://github.com/bytedance/Dolphin, ``demo_page.py``), which is also the
inference script used for the official OmniDocBench evaluation. The two-stage
flow is:

1. Stage 1 (layout): ``"Parse the reading order of this document."`` on the
   full page produces a layout string with bboxes, labels, and tags.
2. Stage 2 (content): element crops are grouped by type (table / formula /
   code / text) and parsed batch-wise with type-specific prompts. Pages whose
   layout parse fails or overlaps heavily are parsed holistically as
   ``distorted_page`` (upstream behaviour for photographed documents).

ROCm notes:
- PyTorch ROCm builds expose GPUs through the ``torch.cuda`` namespace.
- The attention implementation defaults to SDPA; flash-attention 2 packages
  are not generally available for gfx1100.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from PIL import Image

from .. import dolphin_parsing as dp
from ..config import RunConfig
from ..contracts import EmptyOutputError, PageResult, validate_success_output
from ..telemetry import PageTimer
from .base import Backend, BackendNotAvailableError

logger = logging.getLogger(__name__)


class TransformersRocmBackend(Backend):
    name = "transformers"

    def __init__(self, config: RunConfig):
        super().__init__(config)
        self.model = None
        self.processor = None
        self.device = config.get("device", "cuda")

    # -- lifecycle ---------------------------------------------------------

    def load(self) -> None:
        import torch
        from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration

        model_path = self.config.get("model_path")
        if not model_path:
            raise ValueError("config.model_path is required for the transformers backend")

        if self.device == "cuda" and not torch.cuda.is_available():
            if self.config.get("allow_cpu_fallback"):
                logger.warning("GPU unavailable; falling back to CPU because allow_cpu_fallback=true")
                self.device = "cpu"
            else:
                raise BackendNotAvailableError(
                    "torch.cuda.is_available() is False and allow_cpu_fallback is disabled. "
                    "Refusing to run on CPU."
                )
        if self.device == "cuda" and not getattr(torch.version, "hip", None):
            logger.warning("torch.version.hip is empty: this is not a ROCm build of PyTorch")

        start = time.perf_counter()
        self.processor = AutoProcessor.from_pretrained(model_path)
        dtype = {"bfloat16": torch.bfloat16, "float16": torch.float16, "float32": torch.float32}[
            self.config.get("dtype", "bfloat16")
        ]
        self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            model_path,
            torch_dtype=dtype if self.device == "cuda" else torch.float32,
            attn_implementation=self.config.get("attn_implementation", "sdpa"),
        )
        self.model.eval()
        self.model.to(self.device)
        self.processor.tokenizer.padding_side = "left"
        self.load_time_seconds = round(time.perf_counter() - start, 2)
        self.loaded = True
        logger.info("Model loaded from %s in %.1fs on %s", model_path, self.load_time_seconds, self.device)

    def close(self) -> None:
        self.model = None
        self.processor = None
        self.loaded = False
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass

    # -- inference primitives ----------------------------------------------

    def chat(self, prompt, image):
        """Run one generation round; accepts a single image or a batch."""
        import torch
        from qwen_vl_utils import process_vision_info

        is_batch = isinstance(image, list)
        images = image if is_batch else [image]
        prompts = prompt if isinstance(prompt, list) else [prompt] * len(images)
        assert len(images) == len(prompts)

        processed_images = [
            dp.resize_img(img, max_size=self.config.get("resize_max_size", 1600)) for img in images
        ]
        all_messages = [
            [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": img},
                        {"type": "text", "text": question},
                    ],
                }
            ]
            for img, question in zip(processed_images, prompts, strict=True)
        ]
        texts = [
            self.processor.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
            for msgs in all_messages
        ]
        all_image_inputs = []
        for msgs in all_messages:
            image_inputs, _video_inputs = process_vision_info(msgs)
            all_image_inputs.extend(image_inputs)

        inputs = self.processor(
            text=texts,
            images=all_image_inputs or None,
            videos=None,
            padding=True,
            return_tensors="pt",
        )
        inputs = inputs.to(self.model.device)

        gen_kwargs = {
            "max_new_tokens": self.config.get("max_new_tokens", 4096),
            "do_sample": False,
            "temperature": None,
        }
        max_time = self.config.get("generation_max_time_seconds")
        if max_time:
            gen_kwargs["max_time"] = float(max_time)

        with torch.inference_mode():
            generated_ids = self.model.generate(**inputs, **gen_kwargs)
        trimmed = [
            out_ids[len(in_ids) :] for in_ids, out_ids in zip(inputs.input_ids, generated_ids, strict=True)
        ]
        results = self.processor.batch_decode(
            trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
        )
        return results if is_batch else results[0]

    # -- page pipeline -------------------------------------------------------

    def parse_page(self, image_path: str | Path, output_dir: str | Path) -> PageResult:
        if not self.loaded:
            raise RuntimeError("Backend not loaded; call load() first")
        image_path = Path(image_path)
        output_dir = Path(output_dir)
        page_id = image_path.stem
        markdown_dir = output_dir / "markdown"
        raw_dir = output_dir / "raw"
        figures_dir = markdown_dir / "figures"
        for d in (markdown_dir, raw_dir, figures_dir):
            d.mkdir(parents=True, exist_ok=True)

        timeout_s = self.config.get("page_timeout_seconds")

        with PageTimer() as timer:
            image = Image.open(image_path).convert("RGB")

            # Stage 1: layout + reading order
            layout_output = self.chat(self.config.get("layout_prompt"), image)

            # Stage 2: element-level parsing
            elements, fallback = self._parse_elements(layout_output, image, figures_dir, page_id)

            markdown = dp.MarkdownConverter(post_process=self.config.get("post_process", False)).convert(
                elements
            )
            validate_success_output(page_id, markdown)

        markdown_path = markdown_dir / f"{page_id}.md"
        markdown_path.write_text(markdown, encoding="utf-8")
        raw_path = raw_dir / f"{page_id}.json"
        raw_payload = {
            "page_id": page_id,
            "source_path": str(image_path),
            "layout_output": layout_output,
            "elements": [{k: v for k, v in e.items() if k != "crop"} for e in elements],
            "fallback_distorted_page": fallback,
        }
        raw_path.write_text(json.dumps(raw_payload, ensure_ascii=False, indent=2), encoding="utf-8")

        status = "success"
        error = None
        if timeout_s and timer.latency_ms and timer.latency_ms > timeout_s * 1000:
            status = "timeout"
            error = f"page exceeded timeout of {timeout_s}s (took {timer.latency_ms / 1000:.1f}s)"

        return PageResult(
            page_id=page_id,
            source_path=str(image_path),
            status=status,
            backend=self.name,
            markdown_path=str(markdown_path),
            raw_output_path=str(raw_path),
            error=error,
            latency_ms=timer.latency_ms,
            peak_vram_mb=timer.peak_vram_mb,
            model_revision=self.config.get("model_revision"),
            config_digest=self.config.digest,
            fallback=False,
            element_count=len(elements),
            extra={"distorted_page_mode": fallback},
        )

    def _parse_elements(self, layout_output: str, image: Image.Image, figures_dir: Path, page_id: str):
        """Group elements by type and parse them batch-wise (upstream logic)."""
        layout_list = dp.parse_layout_string(layout_output)
        distorted = False
        if not layout_list or not (layout_output.startswith("[") and layout_output.endswith("]")):
            layout_list = [([0, 0, *image.size], "distorted_page", [])]
            distorted = True
        elif len(layout_list) > 1 and dp.check_bbox_overlap(layout_list, image):
            layout_list = [([0, 0, *image.size], "distorted_page", [])]
            distorted = True

        groups: dict[str, list[dict]] = {"tab": [], "equ": [], "code": [], "text": []}
        figure_results: list[dict] = []
        reading_order = 0

        for bbox, label, tags in layout_list:
            try:
                if label == "distorted_page":
                    x1, y1, x2, y2 = 0, 0, *image.size
                    pil_crop = image
                else:
                    x1, y1, x2, y2 = dp.process_coordinates(bbox, image)
                    pil_crop = image.crop((x1, y1, x2, y2))

                if pil_crop.size[0] > 3 and pil_crop.size[1] > 3:
                    if label == "fig":
                        figure_filename = f"{page_id}_figure_{reading_order:03d}.png"
                        try:
                            pil_crop.save(figures_dir / figure_filename, format="PNG")
                        except OSError as exc:
                            logger.warning("Failed to save figure %s: %s", figure_filename, exc)
                        figure_results.append(
                            {
                                "label": label,
                                "text": f"![Figure](figures/{figure_filename})",
                                "figure_path": f"figures/{figure_filename}",
                                "bbox": [x1, y1, x2, y2],
                                "reading_order": reading_order,
                                "tags": tags,
                            }
                        )
                    else:
                        element = {
                            "crop": pil_crop,
                            "label": label,
                            "bbox": [x1, y1, x2, y2],
                            "reading_order": reading_order,
                            "tags": tags,
                        }
                        key = label if label in ("tab", "equ", "code") else "text"
                        groups[key].append(element)
                reading_order += 1
            except Exception as exc:  # noqa: BLE001 - per-element resilience, mirrors upstream
                logger.warning("Error processing bbox with label %s: %s", label, exc)
                continue

        results = list(figure_results)
        prompts = self.config.get("prompts", {})
        for key in ("tab", "equ", "code", "text"):
            if groups[key]:
                results.extend(self._process_element_batch(groups[key], prompts.get(key)))
        results.sort(key=lambda x: x.get("reading_order", 0))
        return results, distorted

    def _process_element_batch(self, elements: list[dict], prompt: str) -> list[dict]:
        results = []
        max_batch_size = self.config.get("max_batch_size") or len(elements)
        batch_size = min(len(elements), max_batch_size)
        for i in range(0, len(elements), batch_size):
            batch = elements[i : i + batch_size]
            crops = [elem["crop"] for elem in batch]
            batch_results = self.chat([prompt] * len(crops), crops)
            for elem, text in zip(batch, batch_results, strict=True):
                results.append(
                    {
                        "label": elem["label"],
                        "bbox": elem["bbox"],
                        "text": text.strip(),
                        "reading_order": elem["reading_order"],
                        "tags": elem["tags"],
                    }
                )
        return results


__all__ = ["TransformersRocmBackend", "BackendNotAvailableError", "EmptyOutputError"]
