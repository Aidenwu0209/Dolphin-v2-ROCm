"""Dolphin-v2 layout/markdown parsing helpers.

Ported from the upstream Dolphin project (https://github.com/bytedance/Dolphin,
``utils/utils.py`` and ``utils/markdown_utils.py``), which is:

    Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
    SPDX-License-Identifier: MIT

The logic is kept behaviourally identical to the upstream demo pipeline (the
same pipeline used for the official OmniDocBench numbers) so that results on
ROCm are comparable with the published CUDA results. Only I/O-free pure
functions live here; they are unit-testable without a GPU.
"""

from __future__ import annotations

import re
from typing import Any

import numpy as np
from PIL import Image

# ---------------------------------------------------------------------------
# Layout string parsing
# ---------------------------------------------------------------------------


def extract_labels_from_string(text: str) -> list[str]:
    """From ``[202,217,921,325][para][author]`` extract ``para`` and ``author``."""
    all_matches = re.findall(r"\[([^\]]+)\]", text)
    labels = []
    for match in all_matches:
        if not re.match(r"^\d+,\d+,\d+,\d+$", match):
            labels.append(match)
    return labels


def parse_layout_string(bbox_str: str) -> list[tuple[list[float], str, list[str]]]:
    """Parse the stage-1 layout string into ``(bbox, label, tags)`` tuples.

    Supports the Dolphin v1.5/v2 format
    ``[x1,y1,x2,y2][label][tag...][PAIR_SEP]`` with optional ``[RELATION_SEP]``
    separators.
    """
    parsed_results = []
    segments = bbox_str.split("[PAIR_SEP]")
    new_segments: list[str] = []
    for seg in segments:
        new_segments.extend(seg.split("[RELATION_SEP]"))
    for segment in new_segments:
        segment = segment.strip()
        if not segment:
            continue
        coord_pattern = r"\[(\d*\.?\d+),(\d*\.?\d+),(\d*\.?\d+),(\d*\.?\d+)\]"
        coord_match = re.search(coord_pattern, segment)
        label_matches = extract_labels_from_string(segment)
        if coord_match and label_matches:
            coords = [float(coord_match.group(i)) for i in range(1, 5)]
            label = label_matches[0].strip()
            parsed_results.append((coords, label, label_matches[1:]))
    return parsed_results


# ---------------------------------------------------------------------------
# Image geometry
# ---------------------------------------------------------------------------


def resize_img(image: Image.Image, max_size: int = 1600, min_size: int = 28) -> Image.Image:
    """Upstream image pre-resize: cap the long edge, enforce a minimum short edge."""
    width, height = image.size
    if max(width, height) < max_size and min(width, height) >= 28:
        return image

    if max(width, height) > max_size:
        if width > height:
            new_width = max_size
            new_height = int(height * (max_size / width))
        else:
            new_height = max_size
            new_width = int(width * (max_size / height))
        image = image.resize((new_width, new_height))
        width, height = image.size

    if min(width, height) < 28:
        if width < height:
            new_width = min_size
            new_height = int(height * (min_size / width))
        else:
            new_height = min_size
            new_width = int(width * (min_size / height))
        image = image.resize((new_width, new_height))

    return image


def process_coordinates(coords: list[float], pil_image: Image.Image) -> tuple[int, int, int, int]:
    """Map model pixel coordinates back onto the original image."""
    from qwen_vl_utils import smart_resize

    original_w, original_h = pil_image.size[:2]
    resized_pil = resize_img(pil_image)
    resized_w, resized_h = resized_pil.size
    resized_h, resized_w = smart_resize(resized_h, resized_w, factor=28, min_pixels=784, max_pixels=2560000)

    w_ratio, h_ratio = original_w / resized_w, original_h / resized_h
    x1 = int(coords[0] * w_ratio)
    y1 = int(coords[1] * h_ratio)
    x2 = int(coords[2] * w_ratio)
    y2 = int(coords[3] * h_ratio)

    x1 = max(0, min(x1, original_w - 1))
    y1 = max(0, min(y1, original_h - 1))
    x2 = max(x1 + 1, min(x2, original_w))
    y2 = max(y1 + 1, min(y2, original_h))
    return x1, y1, x2, y2


def calculate_iou_matrix(boxes: list[list[float]]) -> np.ndarray:
    boxes_arr = np.array(boxes)
    areas = (boxes_arr[:, 2] - boxes_arr[:, 0]) * (boxes_arr[:, 3] - boxes_arr[:, 1])
    lt = np.maximum(boxes_arr[:, None, :2], boxes_arr[None, :, :2])
    rb = np.minimum(boxes_arr[:, None, 2:], boxes_arr[None, :, 2:])
    wh = np.clip(rb - lt, 0, None)
    inter = wh[:, :, 0] * wh[:, :, 1]
    union = areas[:, None] + areas[None, :] - inter
    return inter / np.clip(union, 1e-6, None)


def check_bbox_overlap(
    layout_results_list: list[tuple[list[float], str, list[str]]],
    image: Image.Image,
    iou_threshold: float = 0.1,
    overlap_box_ratio: float = 0.25,
) -> bool:
    """Detect photographed/distorted pages via heavy bbox overlap (upstream heuristic)."""
    if len(layout_results_list) <= 1:
        return False
    bboxes = []
    for bbox, _label, _tags in layout_results_list:
        x1, y1, x2, y2 = process_coordinates(bbox, image)
        bboxes.append([x1, y1, x2, y2])
    iou_matrix = calculate_iou_matrix(bboxes)
    overlap_mask = iou_matrix > iou_threshold
    np.fill_diagonal(overlap_mask, False)
    has_overlap = overlap_mask.any(axis=1)
    overlap_ratio = has_overlap.sum() / len(bboxes)
    return bool(overlap_ratio > overlap_box_ratio)


# ---------------------------------------------------------------------------
# Markdown conversion (behavioural port of upstream MarkdownConverter)
# ---------------------------------------------------------------------------


def extract_table_from_html(html_string: str) -> str:
    try:
        table_pattern = re.compile(r"<table.*?>.*?</table>", re.DOTALL)
        tables = table_pattern.findall(html_string)
        tables = [re.sub(r"<table[^>]*>", "<table>", table) for table in tables]
        return "\n".join(tables)
    except Exception as exc:  # noqa: BLE001 - mirror upstream defensive behaviour
        return f"<table><tr><td>Error extracting table: {exc}</td></tr></table>"


def remove_numeric_quad_ending(s: str) -> str:
    return re.sub(r"\\quad\([^)]*\)", "", s)


def aligned_to_array(latex: str) -> str:
    pattern = re.compile(r"\\begin\{aligned\}(.*?)\\end\{aligned\}", flags=re.DOTALL)

    def repl(match: re.Match) -> str:
        content = match.group(1).strip()
        new_content = content.replace("&", "")
        return f"\\begin{{array}}{{l}}\n{new_content}\n\\end{{array}}"

    return pattern.sub(repl, latex)


def gathered_to_aligned(latex: str) -> str:
    latex = latex.replace(r"\begin{gathered}", r"\begin{aligned}")
    latex = latex.replace(r"\end{gathered}", r"\end{aligned}")
    return latex


def replace_repeated_cdots(latex: str) -> str:
    return re.sub(r"(\\cdots\s*){3,}", r"\\cdots$$", latex)


def truncate_repeated_tail(s: str, threshold: int = 20, keep: int = 1) -> str:
    if not s:
        return s
    max_pattern_len = min(100, len(s) // threshold)
    for pattern_len in range(1, max_pattern_len + 1):
        if len(s) < pattern_len:
            break
        pattern = s[-pattern_len:]
        count = 0
        pos = len(s)
        while pos >= pattern_len:
            if s[pos - pattern_len : pos] == pattern:
                count += 1
                pos -= pattern_len
            else:
                break
        if count > threshold:
            return s[:pos] + pattern * keep
    return s


class MarkdownConverter:
    """Convert structured recognition results to Markdown (upstream port)."""

    def __init__(self, post_process: bool = False):
        self.post_process = post_process
        self.heading_levels = {
            "sec_0": "#",
            "sec_1": "##",
            "sec_2": "###",
            "sec_3": "###",
            "sec_4": "###",
            "sec_5": "###",
        }
        self.replace_dict = {
            "\\bm": "\\mathbf ",
            "\\eqno": "\\quad ",
            "\\quad": "\\quad ",
            "\\leq": "\\leq ",
            "\\pm": "\\pm ",
            "\\varmathbb": "\\mathbb ",
            "\\in fty": "\\infty",
            "\\mu": "\\mu ",
            "\\cdot": "\\cdot ",
            "\\langle": "\\langle ",
        }

    def try_remove_newline(self, text: str) -> str:
        text = text.strip()
        text = text.replace("-\n", "")

        def is_chinese(char: str) -> bool:
            return "\u4e00" <= char <= "\u9fff"

        lines = text.split("\n")
        processed_lines = []
        for i in range(len(lines) - 1):
            current_line = lines[i].strip()
            next_line = lines[i + 1].strip()
            if current_line:
                if next_line:
                    if is_chinese(current_line[-1]) and is_chinese(next_line[0]):
                        processed_lines.append(current_line)
                    else:
                        processed_lines.append(current_line + " ")
                else:
                    processed_lines.append(current_line + "\n")
            else:
                processed_lines.append("\n")
        if lines and lines[-1].strip():
            processed_lines.append(lines[-1].strip())
        return "".join(processed_lines)

    def _process_formulas_in_text(self, text: str) -> str:
        text = text.replace(r"\upmu", r"\mu")
        for key, value in self.replace_dict.items():
            text = text.replace(key, value)
        return text

    def _handle_text(self, text: str) -> str:
        if not text:
            return ""
        text = self._process_formulas_in_text(text)
        if self.post_process:
            text = replace_repeated_cdots(text)
        return self.try_remove_newline(text)

    def _remove_newline_in_heading(self, text: str) -> str:
        def is_chinese(char: str) -> bool:
            return "\u4e00" <= char <= "\u9fff"

        if any(is_chinese(char) for char in text):
            return text.replace("\n", "")
        return text.replace("\n", " ")

    def _handle_heading(self, text: str, label: str) -> str:
        level = self.heading_levels.get(label, "#")
        text = self._remove_newline_in_heading(text.strip())
        text = self._handle_text(text)
        return f"{level} {text}\n\n"

    def _handle_list_item(self, text: str) -> str:
        return f"- {text.strip()}\n"

    def _handle_figure(self, text: str, section_count: int) -> str:
        if text.startswith("figures/"):
            return f"![Figure {section_count}](../{text})\n\n"
        if text.startswith("!["):
            return f"{text}\n\n"
        if text.startswith("data:image/"):
            return f"![Figure {section_count}]({text})\n\n"
        if ";" in text and "," in text:
            return f"![Figure {section_count}]({text})\n\n"
        return f"![Figure {section_count}](data:image/png;base64,{text})\n\n"

    def _handle_table(self, text: str) -> str:
        markdown_table = text if self.post_process else extract_table_from_html(text)
        return markdown_table + "\n\n"

    def _handle_formula(self, text: str) -> str:
        if self.post_process:
            text = remove_numeric_quad_ending(text)
            text = gathered_to_aligned(text)
            text = aligned_to_array(text)
            text = replace_repeated_cdots(text)
            return f"{text}\n\n"
        text = text.strip("$").rstrip("\\ ").replace(r"\upmu", r"\mu")
        for key, value in self.replace_dict.items():
            text = text.replace(key, value)
        return f"$${text}$$\n\n"

    def convert(self, recognition_results: list[dict[str, Any]]) -> str:
        markdown_content = []
        for section_count, result in enumerate(recognition_results):
            label = result.get("label", "")
            text = result.get("text", "").strip()
            if self.post_process:
                text = truncate_repeated_tail(text, threshold=20, keep=1)
            if not text:
                continue
            if label in {"sec_0", "sec_1", "sec_2", "sec_3", "sec_4", "sec_5", "sec"}:
                markdown_content.append(self._handle_heading(text, label))
            elif label == "fig":
                markdown_content.append(self._handle_figure(text, section_count))
            elif label == "tab":
                markdown_content.append(self._handle_table(text))
            elif label == "equ":
                markdown_content.append(self._handle_formula(text))
            elif label == "list":
                markdown_content.append(self._handle_list_item(text))
            elif label == "code":
                markdown_content.append(f"```bash\n{text}\n```\n\n")
            elif label == "distorted_page":
                markdown_content.append(f"{text}\n\n")
            else:
                markdown_content.append(f"{self._handle_text(text)}\n\n")
        return "".join(markdown_content)
