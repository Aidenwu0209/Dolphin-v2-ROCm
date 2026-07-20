"""Mock backend for CI and contract tests.

Produces deterministic fake markdown without any model dependency. Behaviour
switches (fail/empty/slow pages) are driven by file-name markers so contract
tests can exercise the failure paths of the pipeline.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from ..contracts import EmptyOutputError, PageResult, validate_success_output
from .base import Backend


class MockBackend(Backend):
    name = "mock"

    def load(self) -> None:
        self.load_time_seconds = 0.0
        self.loaded = True

    def close(self) -> None:
        self.loaded = False

    def parse_page(self, image_path: str | Path, output_dir: str | Path) -> PageResult:
        if not self.loaded:
            raise RuntimeError("Backend not loaded; call load() first")
        image_path = Path(image_path)
        output_dir = Path(output_dir)
        page_id = image_path.stem
        markdown_dir = output_dir / "markdown"
        raw_dir = output_dir / "raw"
        markdown_dir.mkdir(parents=True, exist_ok=True)
        raw_dir.mkdir(parents=True, exist_ok=True)

        start = time.perf_counter()
        if "FAIL" in page_id:
            raise RuntimeError(f"mock backend forced failure for {page_id}")
        if "SLOW" in page_id:
            time.sleep(0.2)

        markdown = (
            "" if "EMPTY" in page_id else f"# Mock output for {page_id}\n\nDeterministic mock content.\n"
        )
        validate_success_output(page_id, markdown)

        markdown_path = markdown_dir / f"{page_id}.md"
        markdown_path.write_text(markdown, encoding="utf-8")
        raw_path = raw_dir / f"{page_id}.json"
        raw_path.write_text(
            json.dumps({"page_id": page_id, "layout_output": "[0,0,10,10][para][PAIR_SEP]"}), encoding="utf-8"
        )
        latency_ms = round((time.perf_counter() - start) * 1000, 1)
        return PageResult(
            page_id=page_id,
            source_path=str(image_path),
            status="success",
            backend=self.name,
            markdown_path=str(markdown_path),
            raw_output_path=str(raw_path),
            latency_ms=latency_ms,
            peak_vram_mb=None,
            model_revision=self.config.get("model_revision"),
            config_digest=self.config.digest,
        )


__all__ = ["MockBackend", "EmptyOutputError"]
