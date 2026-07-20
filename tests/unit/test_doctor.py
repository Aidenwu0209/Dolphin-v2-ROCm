from dolphin_v2_rocm.doctor import (
    FAIL,
    PASS,
    WARN,
    check_disk,
    check_env_vars,
    check_model_cache,
    render_markdown,
    run_doctor,
)


def test_run_doctor_returns_machine_readable_report():
    report = run_doctor()
    assert report["overall"] in (PASS, WARN, FAIL)
    assert isinstance(report["checks"], list)
    names = [c["name"] for c in report["checks"]]
    for expected in ("os", "cpu_memory", "disk", "rocm", "torch", "bf16_gpu_compute", "packages", "env_vars"):
        assert expected in names
    for check in report["checks"]:
        assert check["status"] in (PASS, WARN, FAIL)
        assert isinstance(check["detail"], str)


def test_overall_is_worst_status():
    report = run_doctor()
    statuses = {c["status"] for c in report["checks"]}
    if FAIL in statuses:
        assert report["overall"] == FAIL
    elif WARN in statuses:
        assert report["overall"] == WARN
    else:
        assert report["overall"] == PASS


def test_hsa_override_flagged(monkeypatch):
    monkeypatch.setenv("HSA_OVERRIDE_GFX_VERSION", "11.0.0")
    check = check_env_vars()
    assert check.status == WARN
    assert "HSA_OVERRIDE_GFX_VERSION" in check.detail


def test_no_override_passes(monkeypatch):
    monkeypatch.delenv("HSA_OVERRIDE_GFX_VERSION", raising=False)
    check = check_env_vars()
    assert check.status == PASS


def test_model_cache_missing_is_warn(tmp_path):
    check = check_model_cache(str(tmp_path / "nonexistent"))
    assert check.status == WARN
    check2 = check_model_cache(None)
    assert check2.status == WARN


def test_disk_check_has_numbers():
    check = check_disk(".")
    assert "free_gb" in check.data
    assert check.data["free_gb"] > 0


def test_render_markdown_contains_table():
    report = run_doctor()
    md = render_markdown(report)
    assert "# Environment Doctor Report" in md
    assert "| Check | Status | Detail |" in md
