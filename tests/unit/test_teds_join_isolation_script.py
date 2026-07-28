import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "run_teds_join_isolation.sh"


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def test_help_documents_isolation_and_fallback_modes():
    result = run_script("--help")

    assert result.returncode == 0
    assert "--mode strict55|fallback47" in result.stdout
    assert "--aggregate-only PATH" in result.stdout
    assert "never writes to the formal Dolphin result directory" in result.stdout


def test_evidence_hashes_driver_and_raw_scorer_output():
    source = SCRIPT.read_text(encoding="utf-8")

    assert 'driver_script.sha256"' in source
    assert "run_teds_join_isolation.sh" in source
    assert "scorer-output.txt" in source
    assert "scorer.log" not in source


def test_dry_run_resolves_parameters_without_touching_paths(tmp_path):
    scratch = tmp_path / "must-not-be-created"
    result = run_script(
        "--dry-run",
        "--mode",
        "fallback47",
        "--teds-workers",
        "2",
        "--match-workers",
        "3",
        "--repeats",
        "5",
        "--scratch-root",
        str(scratch),
        "--gt-json",
        str(tmp_path / "missing-gt.json"),
        "--pred-dir",
        str(tmp_path / "missing-predictions"),
        "--scorer-src",
        str(tmp_path / "missing-scorer"),
        "--eval-env",
        str(tmp_path / "missing-env"),
    )

    assert result.returncode == 0, result.stderr
    assert "DRY_RUN" in result.stdout
    assert "mode=fallback47" in result.stdout
    assert "expected_pages=47" in result.stdout
    assert "expected_teds_sample_count=86" in result.stdout
    assert "teds_workers=2" in result.stdout
    assert "match_workers=3" in result.stdout
    assert "repeats=5" in result.stdout
    assert "writes_formal_results=false" in result.stdout
    assert "writes_canonical_scorer_result=false" in result.stdout
    assert not scratch.exists()


def test_dry_run_derives_repo_relative_defaults_from_repo_root(tmp_path):
    repo_root = tmp_path / "alternate-repo"
    result = run_script(
        "--dry-run",
        "--repo-root",
        str(repo_root),
    )

    assert result.returncode == 0, result.stderr
    assert f"pred_dir={repo_root}/results/omnidocbench/v16/linux-rocm/markdown" in result.stdout
    assert f"page_list={repo_root}/eval/configs/cuda5070ti_teds_error_pages.txt" in result.stdout


def test_dry_run_rejects_invalid_worker_or_repeat_counts():
    for option in ("--teds-workers", "--match-workers", "--repeats"):
        result = run_script("--dry-run", option, "0")
        assert result.returncode != 0
        assert "must be a positive integer" in result.stderr


def test_aggregate_only_validates_three_fallback_repeats_without_scorer(tmp_path):
    for repeat in (1, 2, 3):
        repeat_dir = tmp_path / f"repeat-{repeat}"
        repeat_dir.mkdir()
        validation = {
            "page_count": 47,
            "match_workers": 4,
            "teds_workers": 1,
            "teds_sample_count": 86,
            "error_case_count": 0,
            "timeout_case_count": 0,
            "exception_case_count": 0,
            "join_error_count": 0,
            "table_teds_sample_all": 0.75,
            "table_teds_page_all": 0.76,
        }
        (repeat_dir / "validation.json").write_text(
            json.dumps(validation),
            encoding="utf-8",
        )

    result = run_script(
        "--aggregate-only",
        str(tmp_path),
        "--mode",
        "fallback47",
        "--repeats",
        "3",
        "--teds-workers",
        "1",
        "--match-workers",
        "4",
    )

    assert result.returncode == 0, result.stderr
    aggregate = json.loads((tmp_path / "aggregate_validation.json").read_text())
    assert aggregate["confirmed"] is True
    assert aggregate["repeat_count"] == 3
    assert aggregate["all_structurally_valid"] is True
    assert aggregate["all_layer_a_vanished"] is True
    assert aggregate["sample_score_exactly_stable"] is True
    assert aggregate["page_score_exactly_stable"] is True


def test_aggregate_only_returns_nonzero_when_join_error_persists(tmp_path):
    for repeat in (1, 2, 3):
        repeat_dir = tmp_path / f"repeat-{repeat}"
        repeat_dir.mkdir()
        validation = {
            "page_count": 55,
            "match_workers": 4,
            "teds_workers": 1,
            "teds_sample_count": 94,
            "error_case_count": 1 if repeat == 2 else 0,
            "timeout_case_count": 0,
            "exception_case_count": 0,
            "join_error_count": 1 if repeat == 2 else 0,
            "table_teds_sample_all": 0.75,
            "table_teds_page_all": 0.76,
        }
        (repeat_dir / "validation.json").write_text(
            json.dumps(validation),
            encoding="utf-8",
        )

    result = run_script(
        "--aggregate-only",
        str(tmp_path),
        "--mode",
        "strict55",
    )

    assert result.returncode == 4
    aggregate = json.loads((tmp_path / "aggregate_validation.json").read_text())
    assert aggregate["confirmed"] is False
    assert aggregate["all_layer_a_vanished"] is False


def test_archives_and_verifies_upstream_tracked_result_before_scoring(tmp_path):
    scorer_clone = tmp_path / "scorer"
    tracked_result = scorer_clone / "result"
    tracked_result.mkdir(parents=True)
    for index in range(10):
        destination = tracked_result / f"example-{index}.json"
        destination.write_text(
            json.dumps({"example": index, "source": "upstream"}),
            encoding="utf-8",
        )

    repeat_dir = tmp_path / "repeat-1"
    repeat_dir.mkdir()
    command = 'source "$1"; archive_upstream_result "$2" "$3" "$4"; test ! -e "$3/result"'
    result = subprocess.run(
        [
            "bash",
            "-c",
            command,
            "bash",
            str(SCRIPT),
            sys.executable,
            str(scorer_clone),
            str(repeat_dir),
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    archive = repeat_dir / "upstream_tracked_result"
    assert not tracked_result.exists()
    assert sorted(path.name for path in archive.glob("*.json")) == [
        f"example-{index}.json" for index in range(10)
    ]

    manifest_path = repeat_dir / "upstream_tracked_result_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["archived"] is True
    assert manifest["file_count"] == 10
    assert manifest["entry_count"] == 10
    assert all(entry["sha256"] for entry in manifest["entries"])
    for entry in manifest["entries"]:
        archived_file = archive / entry["path"]
        assert entry["sha256"] == hashlib.sha256(archived_file.read_bytes()).hexdigest()

    manifest_hash = repeat_dir / "upstream_tracked_result_manifest.sha256"
    digest, filename = manifest_hash.read_text(encoding="utf-8").strip().split("  ", maxsplit=1)
    assert filename == "upstream_tracked_result_manifest.json"
    assert digest == hashlib.sha256(manifest_path.read_bytes()).hexdigest()
