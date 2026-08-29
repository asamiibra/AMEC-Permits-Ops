from types import SimpleNamespace

import pytest
from openpyxl import load_workbook

from backend.app.fixtures.canonical import CANONICAL_PROJECTION_SHEET, CANONICAL_PROJECT_IDS, canonical_workbook_path
from backend.app.services import canonical_workbook as module


def _settings(**overrides):
    values = {
        "app_env": "AZURE-PREPROD",
        "synthetic_only": True,
        "real_data_allowed": False,
        "storage_provider": "mock",
        "synology_mode": "SYNTHETIC",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _prepare(monkeypatch, tmp_path):
    root = tmp_path / "workspace"
    monkeypatch.setenv("SYNTHETIC_TEST_ROOT", str(root))
    monkeypatch.setenv("MOCK_SYSTEMS_ROOT", str(root / "mock-systems"))
    path = canonical_workbook_path()
    module.ensure_canonical_workbook(path)
    return path


def _human_values(path):
    workbook = load_workbook(path, data_only=False)
    try:
        return {sheet: tuple(tuple(cell.value for cell in row) for row in workbook[sheet].iter_rows()) for sheet in module.HUMAN_HEADERS}
    finally:
        workbook.close()


def _force_permission_error(monkeypatch):
    monkeypatch.setattr(module.os, "replace", lambda *_args: (_ for _ in ()).throw(PermissionError("simulated Azure Files replace denial")))


def _write(path, project=CANONICAL_PROJECT_IDS[0], status="SEEDED"):
    return module.write_system_projection(path, project, {"Canonical Plot Number": "001234", "Canonical PIN": "PIN-000123", "Rendering Version": "R1.0", "Municipality Request": "GHCE-APP-0142", "Projection Status": status})


def test_t1_normal_atomic_path(monkeypatch, tmp_path):
    path = _prepare(monkeypatch, tmp_path)
    result = _write(path)
    assert result["write_mode"] == "ATOMIC_REPLACE"


def test_t2_permission_error_uses_bounded_preprod_fallback(monkeypatch, tmp_path):
    path = _prepare(monkeypatch, tmp_path)
    monkeypatch.setattr(module, "get_settings", lambda: _settings())
    _force_permission_error(monkeypatch)
    result = _write(path)
    assert result["write_mode"] == "SYNTHETIC_AZURE_FILES_BOUNDED_OVERWRITE"


@pytest.mark.parametrize("settings", [{"app_env": "TEST"}, {"real_data_allowed": True}, {"storage_provider": "smb"}, {"synology_mode": "REAL"}])
def test_t3_to_t6_permission_error_is_not_fallback_outside_exact_contract(monkeypatch, tmp_path, settings):
    path = _prepare(monkeypatch, tmp_path)
    before = path.read_bytes()
    monkeypatch.setattr(module, "get_settings", lambda: _settings(**settings))
    _force_permission_error(monkeypatch)
    with pytest.raises(PermissionError):
        _write(path)
    assert path.read_bytes() == before


def test_t7_wrong_workbook_path_forbids_fallback(monkeypatch, tmp_path):
    path = _prepare(monkeypatch, tmp_path)
    wrong = tmp_path / "other.xlsx"
    module.ensure_canonical_workbook(wrong)
    before = wrong.read_bytes()
    monkeypatch.setattr(module, "get_settings", lambda: _settings())
    _force_permission_error(monkeypatch)
    with pytest.raises(PermissionError):
        _write(wrong)
    assert wrong.read_bytes() == before


def test_t8_human_sheets_are_preserved(monkeypatch, tmp_path):
    path = _prepare(monkeypatch, tmp_path)
    before = _human_values(path)
    _write(path)
    assert _human_values(path) == before


def test_t9_projection_isolation(monkeypatch, tmp_path):
    path = _prepare(monkeypatch, tmp_path)
    before = _human_values(path)
    _write(path)
    workbook = load_workbook(path, data_only=True)
    try:
        sheet = workbook[CANONICAL_PROJECTION_SHEET]
        assert sheet["B2"].value == "001234"
        assert sheet["F2"].value == "SEEDED"
    finally:
        workbook.close()
    assert _human_values(path) == before


def test_t10_four_sequential_canonical_projects_under_fallback(monkeypatch, tmp_path):
    path = _prepare(monkeypatch, tmp_path)
    monkeypatch.setattr(module, "get_settings", lambda: _settings())
    _force_permission_error(monkeypatch)
    for index, project in enumerate(CANONICAL_PROJECT_IDS):
        result = module.write_system_projection(path, project, {"Canonical Plot Number": f"00{index + 1234}", "Canonical PIN": f"PIN-{index:06d}", "Rendering Version": "R1.0", "Municipality Request": f"GHCE-APP-{index + 142:04d}", "Projection Status": "SEEDED"})
        assert result["write_mode"] == "SYNTHETIC_AZURE_FILES_BOUNDED_OVERWRITE"
    workbook = load_workbook(path, data_only=True)
    try:
        sheet = workbook[CANONICAL_PROJECTION_SHEET]
        assert [sheet.cell(row, 1).value for row in range(2, 6)] == CANONICAL_PROJECT_IDS
        assert [sheet.cell(row, 6).value for row in range(2, 6)] == ["SEEDED"] * 4
    finally:
        workbook.close()


def test_t11_invalid_temporary_candidate_leaves_destination_unchanged(monkeypatch, tmp_path):
    path = _prepare(monkeypatch, tmp_path)
    before = path.read_bytes()
    original = module._validate_workbook_candidate
    monkeypatch.setattr(module, "_validate_workbook_candidate", lambda candidate, *args: (_ for _ in ()).throw(module.WorkbookWriteError("TEMP_WORKBOOK_VALIDATION=FAIL")) if candidate != path else original(candidate, *args))
    with pytest.raises(module.WorkbookWriteError, match="TEMP_WORKBOOK_VALIDATION=FAIL"):
        _write(path)
    assert path.read_bytes() == before


def test_t12_bounded_overwrite_failure_restores_original(monkeypatch, tmp_path):
    path = _prepare(monkeypatch, tmp_path)
    before = path.read_bytes()
    monkeypatch.setattr(module, "get_settings", lambda: _settings())
    _force_permission_error(monkeypatch)
    original_write = module._write_full_file
    calls = {"count": 0}
    def fail_once(destination, content):
        calls["count"] += 1
        if calls["count"] == 1:
            raise PermissionError("simulated bounded overwrite failure")
        return original_write(destination, content)
    monkeypatch.setattr(module, "_write_full_file", fail_once)
    with pytest.raises(module.WorkbookWriteError):
        _write(path)
    assert path.read_bytes() == before


def test_t13_postwrite_validation_failure_restores_original(monkeypatch, tmp_path):
    path = _prepare(monkeypatch, tmp_path)
    before = path.read_bytes()
    monkeypatch.setattr(module, "get_settings", lambda: _settings())
    _force_permission_error(monkeypatch)
    original = module._validate_workbook_candidate
    monkeypatch.setattr(module, "_validate_workbook_candidate", lambda candidate, *args: (_ for _ in ()).throw(module.WorkbookWriteError("POSTWRITE_READBACK=FAIL")) if candidate == path else original(candidate, *args))
    with pytest.raises(module.WorkbookWriteError, match="SYNTHETIC_AZURE_FILES_BOUNDED_OVERWRITE=FAIL"):
        _write(path)
    assert path.read_bytes() == before


def test_t14_lock_behavior_is_unchanged(monkeypatch, tmp_path):
    path = _prepare(monkeypatch, tmp_path)
    lock = path.with_suffix(path.suffix + ".lock")
    lock.write_text("synthetic lock", encoding="utf-8")
    try:
        with pytest.raises(module.WorkbookLockedError, match="MANUAL_COPY_REQUIRED"):
            _write(path)
    finally:
        lock.unlink()


def test_t15_temporary_file_removed_after_success(monkeypatch, tmp_path):
    path = _prepare(monkeypatch, tmp_path)
    _write(path)
    assert not list(path.parent.glob("permitops-excel-*.xlsx"))


def test_t16_temporary_file_removed_after_terminal_failure(monkeypatch, tmp_path):
    path = _prepare(monkeypatch, tmp_path)
    monkeypatch.setattr(module.os, "replace", lambda *_args: (_ for _ in ()).throw(OSError("simulated non-permission failure")))
    with pytest.raises(OSError):
        _write(path)
    assert not list(path.parent.glob("permitops-excel-*.xlsx"))
