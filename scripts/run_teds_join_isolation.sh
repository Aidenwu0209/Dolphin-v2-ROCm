#!/usr/bin/env bash
# Isolate OmniDocBench TEDS worker lifecycle failures without touching formal results.
#
# The scorer is run from a fresh local clone for every repeat. Only table TEDS is
# enabled; page matching and TEDS worker counts remain independently configurable.
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

REPO_ROOT="${DEFAULT_REPO_ROOT}"
SCORER_SRC="/root/workspace/OmniDocBench"
EVAL_ENV="/root/workspace/envs/odb-eval"
GT_JSON="/root/workspace/data/OmniDocBench/OmniDocBench.json"
PRED_DIR="${DEFAULT_REPO_ROOT}/results/omnidocbench/v16/linux-rocm/markdown"
PAGE_LIST="${DEFAULT_REPO_ROOT}/eval/configs/cuda5070ti_teds_error_pages.txt"
PRED_DIR_EXPLICIT=0
PAGE_LIST_EXPLICIT=0
SCRATCH_ROOT="${WORKSPACE:-/root/workspace}/teds-join-isolation"
SCORER_COMMIT="2b161d010d2e3aff77a0edef359ea3a6411d23cd"
GT_SHA256="a45cd84b04ad8b793e775089640e6b681209abea33ead54c1828ddca35fae496"
MODE="strict55"
TEDS_WORKERS=1
MATCH_WORKERS=4
REPEATS=3
DRY_RUN=0
AGGREGATE_ONLY=""

usage() {
  cat <<'EOF'
Usage: scripts/run_teds_join_isolation.sh [options]

Run a TEDS-only scorer isolation experiment in a unique scratch directory.
The script never writes to the formal Dolphin result directory or to the
canonical OmniDocBench result directory.

Input selection:
  --mode strict55|fallback47
      strict55   Require predictions for all 55 inventoried join-error pages.
      fallback47 Require exactly 47 available predictions from the 55-page list.
  --gt-json PATH             Full pinned OmniDocBench.json.
  --pred-dir PATH            Directory containing <image-stem>.md predictions.
  --page-list PATH           The 55-page TEDS error inventory list.

Scorer:
  --scorer-src PATH          Pinned OmniDocBench git checkout.
  --eval-env PATH            Evaluation venv containing omnidocbench-eval.
  --scorer-commit SHA        Required scorer commit.
  --teds-workers N           TEDS workers per repeat (default: 1).
  --match-workers N          Page-match workers per repeat (default: 4).
  --repeats N                Number of independent repeats (default: 3).

Evidence and validation:
  --scratch-root PATH        Parent for the unique evidence directory.
  --repo-root PATH           Dolphin-v2-ROCm checkout used for provenance.
  --gt-sha256 SHA|none       Required full-GT digest, or "none" to skip digest check.
  --dry-run                  Print the resolved plan without reading or writing paths.
  --aggregate-only PATH      Rebuild aggregate_validation.json from repeat outputs.
  -h, --help                 Show this help.

Examples:
  scripts/run_teds_join_isolation.sh --mode strict55
  scripts/run_teds_join_isolation.sh --mode fallback47 --repeats 3
  scripts/run_teds_join_isolation.sh --dry-run --mode strict55 --teds-workers 1
EOF
}

die() {
  echo "ERROR: $*" >&2
  exit 2
}

require_value() {
  local option="$1"
  local value="${2:-}"
  [[ -n "${value}" ]] || die "${option} requires a value"
}

require_positive_int() {
  local option="$1"
  local value="$2"
  [[ "${value}" =~ ^[1-9][0-9]*$ ]] || die "${option} must be a positive integer: ${value}"
}

resolve_path() {
  local python_bin="$1"
  local path="$2"
  "${python_bin}" - "${path}" <<'PY'
import sys
from pathlib import Path

print(Path(sys.argv[1]).expanduser().resolve())
PY
}

aggregate_results() {
  local python_bin="$1"
  local experiment_dir="$2"
  local expected_pages="$3"
  local expected_tables="$4"
  local repeats="$5"
  local teds_workers="$6"
  local match_workers="$7"

  "${python_bin}" - \
    "${experiment_dir}" "${expected_pages}" "${expected_tables}" \
    "${repeats}" "${teds_workers}" "${match_workers}" <<'PY'
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
expected_pages = int(sys.argv[2])
expected_tables = int(sys.argv[3])
repeats = int(sys.argv[4])
expected_teds_workers = int(sys.argv[5])
expected_match_workers = int(sys.argv[6])

paths = [root / f"repeat-{repeat}" / "validation.json" for repeat in range(1, repeats + 1)]
missing = [str(path) for path in paths if not path.is_file()]
if missing:
    raise SystemExit("missing repeat validation files:\n" + "\n".join(missing))

rows = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
sample_scores = [row["table_teds_sample_all"] for row in rows]
page_scores = [row["table_teds_page_all"] for row in rows]

all_structurally_valid = all(
    row.get("page_count") == expected_pages
    and row.get("match_workers") == expected_match_workers
    and row.get("teds_workers") == expected_teds_workers
    and row.get("teds_sample_count") == expected_tables
    for row in rows
)
all_layer_a_vanished = all(
    row.get("error_case_count") == 0
    and row.get("timeout_case_count") == 0
    and row.get("exception_case_count") == 0
    and row.get("join_error_count") == 0
    for row in rows
)

aggregate = {
    "repeat_count": len(rows),
    "required_repeat_count": repeats,
    "minimum_confirmation_repeats": 3,
    "expected_page_count": expected_pages,
    "expected_teds_sample_count": expected_tables,
    "expected_match_workers": expected_match_workers,
    "expected_teds_workers": expected_teds_workers,
    "all_structurally_valid": all_structurally_valid,
    "all_layer_a_vanished": all_layer_a_vanished,
    "sample_scores": sample_scores,
    "page_scores": page_scores,
    "sample_score_exactly_stable": len(set(sample_scores)) == 1,
    "page_score_exactly_stable": len(set(page_scores)) == 1,
}
aggregate["confirmed"] = (
    len(rows) >= 3
    and all_structurally_valid
    and all_layer_a_vanished
)

output = root / "aggregate_validation.json"
output.write_text(json.dumps(aggregate, indent=2), encoding="utf-8")
print(json.dumps(aggregate, indent=2))
raise SystemExit(0 if aggregate["confirmed"] else 4)
PY
}

archive_upstream_result() {
  local python_bin="$1"
  local scorer_clone="$2"
  local repeat_dir="$3"

  "${python_bin}" - "${scorer_clone}" "${repeat_dir}" <<'PY'
import hashlib
import json
import os
import sys
from pathlib import Path

scorer_clone = Path(sys.argv[1])
repeat_dir = Path(sys.argv[2])
source = scorer_clone / "result"
archive = repeat_dir / "upstream_tracked_result"
manifest_path = repeat_dir / "upstream_tracked_result_manifest.json"
manifest_hash_path = repeat_dir / "upstream_tracked_result_manifest.sha256"


def digest_bytes(data):
    return hashlib.sha256(data).hexdigest()


def tree_entries(root):
    entries = []
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix()
        stat = path.lstat()
        common = {
            "path": relative,
            "mode": oct(stat.st_mode & 0o777),
        }
        if path.is_symlink():
            target = os.readlink(path)
            entries.append(
                common
                | {
                    "type": "symlink",
                    "target": target,
                    "sha256": digest_bytes(target.encode("utf-8")),
                }
            )
        elif path.is_file():
            entries.append(
                common
                | {
                    "type": "file",
                    "size": stat.st_size,
                    "sha256": digest_bytes(path.read_bytes()),
                }
            )
        elif path.is_dir():
            entries.append(common | {"type": "directory"})
        else:
            raise SystemExit(f"unsupported tracked result entry: {path}")
    return entries


if archive.exists():
    raise SystemExit(f"archive destination already exists: {archive}")

if source.exists():
    before = tree_entries(source)
    source.rename(archive)
    if source.exists() or not archive.is_dir():
        raise SystemExit("tracked result directory was not moved atomically")
    after = tree_entries(archive)
    if before != after:
        raise SystemExit("tracked result archive failed file-list/hash verification")
    archived = True
    entries = after
else:
    archived = False
    entries = []

manifest = {
    "schema_version": 1,
    "archived": archived,
    "source": "scorer/result",
    "archive": "upstream_tracked_result",
    "entry_count": len(entries),
    "file_count": sum(entry["type"] == "file" for entry in entries),
    "directory_count": sum(entry["type"] == "directory" for entry in entries),
    "symlink_count": sum(entry["type"] == "symlink" for entry in entries),
    "entries": entries,
}
manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
manifest_path.write_bytes(manifest_bytes)
manifest_hash_path.write_text(
    f"{digest_bytes(manifest_bytes)}  {manifest_path.name}\n",
    encoding="utf-8",
)
print(
    f"upstream result archived={archived} "
    f"files={manifest['file_count']} entries={manifest['entry_count']}"
)
PY
}

if [[ "${BASH_SOURCE[0]}" != "$0" ]]; then
  return 0
fi

while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --repo-root)
      require_value "$1" "${2:-}"
      REPO_ROOT="$2"
      shift 2
      ;;
    --scorer-src)
      require_value "$1" "${2:-}"
      SCORER_SRC="$2"
      shift 2
      ;;
    --eval-env)
      require_value "$1" "${2:-}"
      EVAL_ENV="$2"
      shift 2
      ;;
    --gt-json)
      require_value "$1" "${2:-}"
      GT_JSON="$2"
      shift 2
      ;;
    --pred-dir)
      require_value "$1" "${2:-}"
      PRED_DIR="$2"
      PRED_DIR_EXPLICIT=1
      shift 2
      ;;
    --page-list)
      require_value "$1" "${2:-}"
      PAGE_LIST="$2"
      PAGE_LIST_EXPLICIT=1
      shift 2
      ;;
    --scratch-root)
      require_value "$1" "${2:-}"
      SCRATCH_ROOT="$2"
      shift 2
      ;;
    --scorer-commit)
      require_value "$1" "${2:-}"
      SCORER_COMMIT="$2"
      shift 2
      ;;
    --gt-sha256)
      require_value "$1" "${2:-}"
      GT_SHA256="$2"
      shift 2
      ;;
    --mode)
      require_value "$1" "${2:-}"
      MODE="$2"
      shift 2
      ;;
    --teds-workers)
      require_value "$1" "${2:-}"
      TEDS_WORKERS="$2"
      shift 2
      ;;
    --match-workers)
      require_value "$1" "${2:-}"
      MATCH_WORKERS="$2"
      shift 2
      ;;
    --repeats)
      require_value "$1" "${2:-}"
      REPEATS="$2"
      shift 2
      ;;
    --aggregate-only)
      require_value "$1" "${2:-}"
      AGGREGATE_ONLY="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "unknown option: $1"
      ;;
  esac
done

if [[ "${PRED_DIR_EXPLICIT}" -eq 0 ]]; then
  PRED_DIR="${REPO_ROOT}/results/omnidocbench/v16/linux-rocm/markdown"
fi
if [[ "${PAGE_LIST_EXPLICIT}" -eq 0 ]]; then
  PAGE_LIST="${REPO_ROOT}/eval/configs/cuda5070ti_teds_error_pages.txt"
fi

case "${MODE}" in
  strict55)
    EXPECTED_PAGES=55
    EXPECTED_TABLES=94
    ;;
  fallback47)
    EXPECTED_PAGES=47
    EXPECTED_TABLES=86
    ;;
  *)
    die "--mode must be strict55 or fallback47: ${MODE}"
    ;;
esac

require_positive_int "--teds-workers" "${TEDS_WORKERS}"
require_positive_int "--match-workers" "${MATCH_WORKERS}"
require_positive_int "--repeats" "${REPEATS}"

if [[ "${GT_SHA256}" != "none" && ! "${GT_SHA256}" =~ ^[0-9a-fA-F]{64}$ ]]; then
  die "--gt-sha256 must be a 64-character hexadecimal digest or none"
fi
if [[ ! "${SCORER_COMMIT}" =~ ^[0-9a-fA-F]{40}$ ]]; then
  die "--scorer-commit must be a full 40-character commit"
fi
if [[ "${DRY_RUN}" -eq 1 && -n "${AGGREGATE_ONLY}" ]]; then
  die "--dry-run and --aggregate-only are mutually exclusive"
fi

if [[ "${DRY_RUN}" -eq 1 ]]; then
  cat <<EOF
DRY_RUN
mode=${MODE}
expected_pages=${EXPECTED_PAGES}
expected_teds_sample_count=${EXPECTED_TABLES}
teds_workers=${TEDS_WORKERS}
match_workers=${MATCH_WORKERS}
repeats=${REPEATS}
repo_root=${REPO_ROOT}
scorer_src=${SCORER_SRC}
eval_env=${EVAL_ENV}
gt_json=${GT_JSON}
pred_dir=${PRED_DIR}
page_list=${PAGE_LIST}
scratch_root=${SCRATCH_ROOT}
scorer_commit=${SCORER_COMMIT}
gt_sha256=${GT_SHA256}
writes_formal_results=false
writes_canonical_scorer_result=false
EOF
  exit 0
fi

if [[ -n "${AGGREGATE_ONLY}" ]]; then
  AGGREGATE_PYTHON="$(command -v python3 || true)"
  [[ -n "${AGGREGATE_PYTHON}" ]] || die "python3 is required for --aggregate-only"
  [[ -d "${AGGREGATE_ONLY}" ]] || die "aggregate directory not found: ${AGGREGATE_ONLY}"
  aggregate_results \
    "${AGGREGATE_PYTHON}" "${AGGREGATE_ONLY}" "${EXPECTED_PAGES}" "${EXPECTED_TABLES}" \
    "${REPEATS}" "${TEDS_WORKERS}" "${MATCH_WORKERS}"
  exit "$?"
fi

git -C "${REPO_ROOT}" rev-parse --is-inside-work-tree >/dev/null 2>&1 || \
  die "Dolphin git checkout not found: ${REPO_ROOT}"
git -C "${SCORER_SRC}" rev-parse --is-inside-work-tree >/dev/null 2>&1 || \
  die "OmniDocBench git checkout not found: ${SCORER_SRC}"
[[ -x "${EVAL_ENV}/bin/python" ]] || die "eval Python not executable: ${EVAL_ENV}/bin/python"
[[ -x "${EVAL_ENV}/bin/omnidocbench-eval" ]] || \
  die "scorer entrypoint not executable: ${EVAL_ENV}/bin/omnidocbench-eval"
[[ -f "${GT_JSON}" ]] || die "ground-truth JSON not found: ${GT_JSON}"
[[ -d "${PRED_DIR}" ]] || die "prediction directory not found: ${PRED_DIR}"
[[ -f "${PAGE_LIST}" ]] || die "page list not found: ${PAGE_LIST}"

ACTUAL_SCORER_COMMIT="$(git -C "${SCORER_SRC}" rev-parse HEAD)"
[[ "${ACTUAL_SCORER_COMMIT}" == "${SCORER_COMMIT}" ]] || \
  die "scorer commit mismatch: expected ${SCORER_COMMIT}, got ${ACTUAL_SCORER_COMMIT}"

if pgrep -af "omnidocbench-eval" >/dev/null 2>&1; then
  die "another omnidocbench-eval process is running; do not overlap isolation runs"
fi

"${EVAL_ENV}/bin/python" - "${GT_JSON}" "${GT_SHA256}" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
expected_hash = sys.argv[2].lower()
data = json.loads(path.read_text(encoding="utf-8"))
if len(data) != 1651:
    raise SystemExit(f"expected 1651 GT records, found {len(data)}")
actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
if expected_hash != "none" and actual_hash != expected_hash:
    raise SystemExit(
        f"GT SHA-256 mismatch: expected {expected_hash}, got {actual_hash}"
    )
print(f"GT records={len(data)} sha256={actual_hash}")
PY

PYTHON_BIN="${EVAL_ENV}/bin/python"
RESOLVED_REPO_ROOT="$(resolve_path "${PYTHON_BIN}" "${REPO_ROOT}")"
RESOLVED_SCORER_SRC="$(resolve_path "${PYTHON_BIN}" "${SCORER_SRC}")"
RESOLVED_PRED_DIR="$(resolve_path "${PYTHON_BIN}" "${PRED_DIR}")"
RESOLVED_SCRATCH_ROOT="$(resolve_path "${PYTHON_BIN}" "${SCRATCH_ROOT}")"

case "${RESOLVED_SCRATCH_ROOT}" in
  "${RESOLVED_REPO_ROOT}"|"${RESOLVED_REPO_ROOT}/"*|\
  "${RESOLVED_SCORER_SRC}"|"${RESOLVED_SCORER_SRC}/"*|\
  "${RESOLVED_PRED_DIR}"|"${RESOLVED_PRED_DIR}/"*)
    die "scratch root must be outside the repo, scorer checkout, and predictions: ${RESOLVED_SCRATCH_ROOT}"
    ;;
esac
[[ "${RESOLVED_SCRATCH_ROOT}" != "/" ]] || die "scratch root cannot be /"

umask 077
mkdir -p "${RESOLVED_SCRATCH_ROOT}"
EXPERIMENT_DIR="$(mktemp -d "${RESOLVED_SCRATCH_ROOT%/}/teds-join-w${TEDS_WORKERS}.XXXXXXXX")"
INPUT_DIR="${EXPERIMENT_DIR}/input"
mkdir -p "${INPUT_DIR}/markdown"
sha256sum "${BASH_SOURCE[0]}" | \
  awk '{print $1 "  run_teds_join_isolation.sh"}' \
  > "${EXPERIMENT_DIR}/driver_script.sha256"

on_error() {
  local rc="$?"
  echo "ERROR: isolation run stopped with exit ${rc}" >&2
  echo "Partial evidence retained at: ${EXPERIMENT_DIR}" >&2
  exit "${rc}"
}
trap on_error ERR

"${PYTHON_BIN}" - \
  "${GT_JSON}" "${PAGE_LIST}" "${PRED_DIR}" "${MODE}" \
  "${EXPECTED_PAGES}" "${EXPECTED_TABLES}" \
  "${INPUT_DIR}/OmniDocBench-teds-subset.json" \
  "${INPUT_DIR}/markdown" "${INPUT_DIR}/input_manifest.json" \
  "${INPUT_DIR}/selected_pages.txt" <<'PY'
import hashlib
import json
import os
import sys
from pathlib import Path

(
    gt_path,
    list_path,
    prediction_dir,
    mode,
    expected_pages,
    expected_tables,
    output_gt,
    output_predictions,
    manifest_path,
    selected_pages_path,
) = sys.argv[1:]

gt_path = Path(gt_path)
list_path = Path(list_path)
prediction_dir = Path(prediction_dir)
expected_pages = int(expected_pages)
expected_tables = int(expected_tables)
output_gt = Path(output_gt)
output_predictions = Path(output_predictions)
manifest_path = Path(manifest_path)
selected_pages_path = Path(selected_pages_path)

inventory_names = [
    line.strip()
    for line in list_path.read_text(encoding="utf-8").splitlines()
    if line.strip() and not line.lstrip().startswith("#")
]
if len(inventory_names) != 55 or len(set(inventory_names)) != 55:
    raise SystemExit(
        f"expected 55 unique inventory pages, found {len(set(inventory_names))}"
    )
unsafe_names = [name for name in inventory_names if Path(name).name != name]
if unsafe_names:
    raise SystemExit(
        "page list entries must be basenames, not paths:\n" + "\n".join(unsafe_names)
    )
stems = [Path(name).stem for name in inventory_names]
if len(set(stems)) != len(stems):
    raise SystemExit("page list contains image names that collide as markdown stems")

available = [
    name
    for name in inventory_names
    if (prediction_dir / f"{Path(name).stem}.md").is_file()
]
if mode == "strict55":
    selected_names = inventory_names
    missing = sorted(set(inventory_names) - set(available))
    if missing:
        raise SystemExit(
            "strict55 requires every prediction; missing:\n" + "\n".join(missing)
        )
elif mode == "fallback47":
    if len(available) != 47:
        raise SystemExit(
            "fallback47 requires exactly 47 available inventory predictions; "
            f"found {len(available)}"
        )
    selected_names = available
else:
    raise SystemExit(f"unsupported mode: {mode}")

if len(selected_names) != expected_pages:
    raise SystemExit(
        f"selected page count mismatch: expected {expected_pages}, "
        f"found {len(selected_names)}"
    )

wanted = set(selected_names)
full_gt = json.loads(gt_path.read_text(encoding="utf-8"))
subset = [
    record
    for record in full_gt
    if Path(record["page_info"]["image_path"]).name in wanted
]
found = {Path(record["page_info"]["image_path"]).name for record in subset}
missing_gt = sorted(wanted - found)
if missing_gt:
    raise SystemExit("selected pages missing from GT:\n" + "\n".join(missing_gt))

table_count = sum(
    det.get("category_type") == "table"
    for record in subset
    for det in record.get("layout_dets", [])
)
if table_count != expected_tables:
    raise SystemExit(
        f"TEDS sample count mismatch: expected {expected_tables}, found {table_count}"
    )

prediction_hashes = {}
for name in selected_names:
    source = prediction_dir / f"{Path(name).stem}.md"
    destination = output_predictions / source.name
    os.symlink(source.resolve(), destination)
    prediction_hashes[source.name] = hashlib.sha256(source.read_bytes()).hexdigest()

output_gt.write_text(
    json.dumps(subset, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
selected_pages_path.write_text(
    "\n".join(selected_names) + "\n",
    encoding="utf-8",
)
manifest = {
    "mode": mode,
    "source_gt_sha256": hashlib.sha256(gt_path.read_bytes()).hexdigest(),
    "subset_gt_sha256": hashlib.sha256(output_gt.read_bytes()).hexdigest(),
    "page_count": len(subset),
    "teds_sample_count": table_count,
    "prediction_count": len(prediction_hashes),
    "prediction_sha256": prediction_hashes,
}
manifest_path.write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
print(
    json.dumps(
        manifest | {"prediction_sha256": f"<{len(prediction_hashes)} hashes>"},
        ensure_ascii=False,
        indent=2,
    )
)
PY

git -C "${REPO_ROOT}" rev-parse HEAD > "${EXPERIMENT_DIR}/dolphin_repo_commit.txt"
git -C "${SCORER_SRC}" rev-parse HEAD > "${EXPERIMENT_DIR}/scorer_commit.txt"
"${PYTHON_BIN}" -V > "${EXPERIMENT_DIR}/python_version.txt" 2>&1
uname -a > "${EXPERIMENT_DIR}/uname.txt"
if ! "${PYTHON_BIN}" -m pip freeze > "${EXPERIMENT_DIR}/pip_freeze.txt" 2>&1; then
  echo "WARN: pip freeze failed; see ${EXPERIMENT_DIR}/pip_freeze.txt" >&2
fi
if [[ -f "${REPO_ROOT}/evidence/accuracy/full-eval/scorer_run_summary.json" ]]; then
  cp \
    "${REPO_ROOT}/evidence/accuracy/full-eval/scorer_run_summary.json" \
    "${EXPERIMENT_DIR}/baseline_workers4_scorer_run_summary.json"
fi

ulimit -n 65536 || ulimit -n 16384 || true

for ((repeat = 1; repeat <= REPEATS; repeat++)); do
  RUN_DIR="${EXPERIMENT_DIR}/repeat-${repeat}"
  mkdir -p "${RUN_DIR}"

  git clone --quiet --local --no-hardlinks "${SCORER_SRC}" "${RUN_DIR}/scorer"
  git -C "${RUN_DIR}/scorer" checkout --quiet --detach "${SCORER_COMMIT}"
  archive_upstream_result "${PYTHON_BIN}" "${RUN_DIR}/scorer" "${RUN_DIR}"
  [[ ! -e "${RUN_DIR}/scorer/result" ]] || \
    die "scorer result path still exists after upstream archive: ${RUN_DIR}/scorer/result"
  mkdir "${RUN_DIR}/scorer/result"
  [[ -z "$(find "${RUN_DIR}/scorer/result" -mindepth 1 -print -quit)" ]] || \
    die "scorer result path is not empty before repeat ${repeat}"

  "${PYTHON_BIN}" - \
    "${INPUT_DIR}/OmniDocBench-teds-subset.json" \
    "${INPUT_DIR}/markdown" "${RUN_DIR}/config.yaml" \
    "${TEDS_WORKERS}" "${MATCH_WORKERS}" <<'PY'
import json
import sys
from pathlib import Path

gt_path = Path(sys.argv[1]).resolve()
prediction_path = Path(sys.argv[2]).resolve()
output_path = Path(sys.argv[3])
teds_workers = int(sys.argv[4])
match_workers = int(sys.argv[5])

config = {
    "end2end_eval": {
        "metrics": {
            "table": {
                "metric": ["TEDS"],
                "teds_workers": teds_workers,
            }
        },
        "dataset": {
            "dataset_name": "end2end_dataset",
            "ground_truth": {"data_path": str(gt_path)},
            "prediction": {"data_path": str(prediction_path)},
            "match_method": "quick_match",
            "match_workers": match_workers,
            "quick_match_truncate_timeout_sec": 300,
            "match_timeout_sec": 420,
            "timeout_fallback_max_chunk_span": 10,
            "timeout_fallback_order_penalty": 0.10,
        },
    }
}
output_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
PY

  STARTED_EPOCH="$(date +%s)"
  date -u +%FT%TZ > "${RUN_DIR}/started_at.txt"
  touch "${RUN_DIR}/scorer_started.marker"

  set +e
  (
    cd "${RUN_DIR}/scorer"
    PYTHONPATH="${RUN_DIR}/scorer${PYTHONPATH:+:${PYTHONPATH}}" \
      "${EVAL_ENV}/bin/omnidocbench-eval" --config "${RUN_DIR}/config.yaml"
  ) 2>&1 | tee "${RUN_DIR}/scorer-output.txt"
  SCORE_RC="${PIPESTATUS[0]}"
  set -e

  FINISHED_EPOCH="$(date +%s)"
  date -u +%FT%TZ > "${RUN_DIR}/finished_at.txt"
  printf 'exit_code=%s\nduration_seconds=%s\n' \
    "${SCORE_RC}" "$((FINISHED_EPOCH - STARTED_EPOCH))" \
    > "${RUN_DIR}/timing.txt"
  [[ "${SCORE_RC}" -eq 0 ]] || die "repeat ${repeat} scorer exit=${SCORE_RC}"
  [[ -d "${RUN_DIR}/scorer/result" ]] || \
    die "repeat ${repeat}: scorer did not create a fresh result directory"

  mapfile -t METRIC_FILES < <(
    find "${RUN_DIR}/scorer/result" -maxdepth 1 -type f \
      -name '*metric_result.json' -newer "${RUN_DIR}/scorer_started.marker" -print
  )
  mapfile -t SUMMARY_FILES < <(
    find "${RUN_DIR}/scorer/result" -maxdepth 1 -type f \
      -name '*run_summary.json' -newer "${RUN_DIR}/scorer_started.marker" -print
  )
  [[ "${#METRIC_FILES[@]}" -eq 1 ]] || \
    die "repeat ${repeat}: expected one fresh metric result, found ${#METRIC_FILES[@]}"
  [[ "${#SUMMARY_FILES[@]}" -eq 1 ]] || \
    die "repeat ${repeat}: expected one fresh scorer summary, found ${#SUMMARY_FILES[@]}"

  cp "${METRIC_FILES[0]}" "${RUN_DIR}/metric_result.json"
  cp "${SUMMARY_FILES[0]}" "${RUN_DIR}/scorer_run_summary.json"
  (
    cd "${RUN_DIR}"
    sha256sum \
      metric_result.json scorer_run_summary.json scorer-output.txt \
      > SHA256SUMS
  )

  "${PYTHON_BIN}" - \
    "${RUN_DIR}/metric_result.json" "${RUN_DIR}/scorer_run_summary.json" \
    "${RUN_DIR}/validation.json" "${EXPECTED_PAGES}" "${EXPECTED_TABLES}" \
    "${TEDS_WORKERS}" "${MATCH_WORKERS}" <<'PY'
import json
import sys
from pathlib import Path

metric_path = Path(sys.argv[1])
summary_path = Path(sys.argv[2])
output_path = Path(sys.argv[3])
expected_pages = int(sys.argv[4])
expected_tables = int(sys.argv[5])
expected_teds_workers = int(sys.argv[6])
expected_match_workers = int(sys.argv[7])

metric = json.loads(metric_path.read_text(encoding="utf-8"))
summary = json.loads(summary_path.read_text(encoding="utf-8"))
page_match = summary["stage_execution"]["page_match"]
teds = summary["stage_execution"]["metrics"]["table"]["TEDS"]
errors = teds.get("error_cases", [])
join_reason = "AssertionError: can only join a started process"

validation = {
    "page_count": page_match.get("page_count"),
    "match_workers": page_match.get("workers"),
    "teds_workers": teds.get("workers"),
    "teds_sample_count": teds.get("sample_count"),
    "error_case_count": teds.get("error_case_count", 0),
    "timeout_case_count": teds.get("timeout_case_count", 0),
    "exception_case_count": teds.get("exception_case_count", 0),
    "join_error_count": sum(
        case.get("reason") == join_reason for case in errors
    ),
    "table_teds_sample_all": metric["table"]["all"]["TEDS"]["all"],
    "table_teds_page_all": metric["table"]["page"]["TEDS"]["ALL"],
}
validation["structurally_valid"] = (
    validation["page_count"] == expected_pages
    and validation["match_workers"] == expected_match_workers
    and validation["teds_workers"] == expected_teds_workers
    and validation["teds_sample_count"] == expected_tables
)
validation["layer_a_vanished"] = (
    validation["error_case_count"] == 0
    and validation["timeout_case_count"] == 0
    and validation["exception_case_count"] == 0
    and validation["join_error_count"] == 0
)
output_path.write_text(json.dumps(validation, indent=2), encoding="utf-8")
print(json.dumps(validation, indent=2))
PY
done

trap - ERR
if aggregate_results \
  "${PYTHON_BIN}" "${EXPERIMENT_DIR}" "${EXPECTED_PAGES}" "${EXPECTED_TABLES}" \
  "${REPEATS}" "${TEDS_WORKERS}" "${MATCH_WORKERS}"; then
  echo "TEDS join isolation confirmed."
  echo "Evidence: ${EXPERIMENT_DIR}"
else
  rc="$?"
  echo "TEDS join isolation did not meet confirmation criteria." >&2
  echo "Evidence retained at: ${EXPERIMENT_DIR}" >&2
  exit "${rc}"
fi
