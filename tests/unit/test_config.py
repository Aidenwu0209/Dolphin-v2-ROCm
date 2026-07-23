from pathlib import Path

import pytest

from dolphin_v2_rocm.config import DEFAULTS, load_config


def test_defaults_applied_without_file():
    cfg = load_config()
    assert cfg["backend"] == "transformers"
    assert cfg["dtype"] == "bfloat16"
    assert cfg["max_new_tokens"] == DEFAULTS["max_new_tokens"]


def test_yaml_overrides_defaults(tmp_path: Path):
    config_file = tmp_path / "run.yaml"
    config_file.write_text("max_new_tokens: 128\nprompts:\n  tab: 'custom table prompt'\n")
    cfg = load_config(config_file)
    assert cfg["max_new_tokens"] == 128
    assert cfg["prompts"]["tab"] == "custom table prompt"
    # nested merge keeps untouched keys
    assert cfg["prompts"]["equ"] == DEFAULTS["prompts"]["equ"]


def test_explicit_overrides_win(tmp_path: Path):
    config_file = tmp_path / "run.yaml"
    config_file.write_text("backend: transformers\n")
    cfg = load_config(config_file, overrides={"backend": "mock", "limit_pages": 3})
    assert cfg["backend"] == "mock"
    assert cfg["limit_pages"] == 3


def test_digest_is_stable_and_sensitive(tmp_path: Path):
    config_file = tmp_path / "run.yaml"
    config_file.write_text("max_new_tokens: 128\n")
    a = load_config(config_file)
    b = load_config(config_file)
    assert a.digest == b.digest
    c = load_config(config_file, overrides={"max_new_tokens": 256})
    assert a.digest != c.digest
    assert a.digest.startswith("sha256:")


def test_non_mapping_config_rejected(tmp_path: Path):
    config_file = tmp_path / "bad.yaml"
    config_file.write_text("- just\n- a\n- list\n")
    with pytest.raises(ValueError):
        load_config(config_file)
