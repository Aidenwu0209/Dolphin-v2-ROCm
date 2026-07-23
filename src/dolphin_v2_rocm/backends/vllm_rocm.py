"""vLLM backend for Dolphin-v2 on ROCm (experimental).

Status: experimental. vLLM support for gfx1100 (RDNA3) is validated
separately from the Transformers baseline; see docs/rocm-notes.md and
evidence/compatibility/ for the current verdict on this platform.

The backend mirrors the two-stage Dolphin pipeline but routes generation
through a vLLM engine. If vLLM is not importable or cannot initialize on the
current GPU, ``load()`` raises :class:`BackendNotAvailableError` with the
original cause preserved; it never silently degrades.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from PIL import Image

from .. import dolphin_parsing as dp
from ..config import RunConfig
from ..contracts import PageResult, validate_success_output
from ..telemetry import PageTimer
from .base import Backend, BackendNotAvailableError

logger = logging.getLogger(__name__)


class VllmRocmBackend(Backend):
    name = "vllm"

    def __init__(self, config: RunConfig):
        super().__init__(config)
        self.llm = None
        self.sampling_params = None

    def load(self) -> None:
        try:
            from vllm import LLM, SamplingParams
        except ImportError as exc:
            raise BackendNotAvailableError(
                "vllm is not installed in this environment; the transformers backend is the "
                "supported baseline on this platform"
            ) from exc

        model_path = self.config.get("model_path")
        if not model_path:
            raise ValueError("config.model_path is required for the vllm backend")

        start = time.perf_counter()
        try:
            self.llm = LLM(
                model=model_path,
                dtype=self.config.get("dtype", "bfloat16"),
                max_model_len=self.config.get("vllm_max_model_len", 8192),
                gpu_memory_utilization=self.config.get("vllm_gpu_memory_utilization", 0.85),
                enforce_eager=self.config.get("vllm_enforce_eager", False),
                limit_mm_per_prompt={"image": 1},
            )
        except Exception as exc:  # noqa: BLE001 - init failures become explicit unavailability
            raise BackendNotAvailableError(f"vLLM engine failed to initialize: {exc}") from exc
        self.sampling_params = SamplingParams(
            temperature=0.0,
            max_tokens=self.config.get("max_new_tokens", 4096),
        )
        self.load_time_seconds = round(time.perf_counter() - start, 2)
        self.loaded = True

    def close(self) -> None:
        self.llm = None
        self.loaded = False

    def chat(self, prompt, image):
        is_batch = isinstance(image, list)
        images = image if is_batch else [image]
        prompts = prompt if isinstance(prompt, list) else [prompt] * len(images)

        requests = []
        for img, question in zip(images, prompts, strict=True):
            resized = dp.resize_img(img, max_size=self.config.get("resize_max_size", 1600))
            requests.append(
                {
                    "prompt": (
                        "<|im_start|>user\n<|vision_start|><|image_pad|><|vision_end|>"
                        f"{question}<|im_end|>\n<|im_start|>assistant\n"
                    ),
                    "multi_modal_data": {"image": resized},
                }
            )
        outputs = self.llm.generate(requests, self.sampling_params)
        results = [out.outputs[0].text for out in outputs]
        return results if is_batch else results[0]

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

        with PageTimer() as timer:
            image = Image.open(image_path).convert("RGB")
            layout_output = self.chat(self.config.get("layout_prompt"), image)
            elements, fallback = self._parse_elements(layout_output, image, figures_dir, page_id)
            markdown = dp.MarkdownConverter(post_process=self.config.get("post_process", False)).convert(
                elements
            )
            validate_success_output(page_id, markdown)

        markdown_path = markdown_dir / f"{page_id}.md"
        markdown_path.write_text(markdown, encoding="utf-8")
        raw_path = raw_dir / f"{page_id}.json"
        raw_path.write_text(
            json.dumps(
                {
                    "page_id": page_id,
                    "source_path": str(image_path),
                    "layout_output": layout_output,
                    "elements": [{k: v for k, v in e.items() if k != "crop"} for e in elements],
                    "fallback_distorted_page": fallback,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return PageResult(
            page_id=page_id,
            source_path=str(image_path),
            status="success",
            backend=self.name,
            markdown_path=str(markdown_path),
            raw_output_path=str(raw_path),
            latency_ms=timer.latency_ms,
            peak_vram_mb=timer.peak_vram_mb,
            model_revision=self.config.get("model_revision"),
            config_digest=self.config.digest,
            element_count=len(elements),
            extra={"distorted_page_mode": fallback},
        )

    # Reuse the same element grouping logic as the transformers backend.
    def _parse_elements(self, layout_output: str, image: Image.Image, figures_dir: Path, page_id: str):
        from .transformers_rocm import TransformersRocmBackend

        return TransformersRocmBackend._parse_elements(self, layout_output, image, figures_dir, page_id)

    def _process_element_batch(self, elements, prompt):
        from .transformers_rocm import TransformersRocmBackend

        return TransformersRocmBackend._process_element_batch(self, elements, prompt)
