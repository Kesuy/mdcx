import os
from pathlib import Path

import mdcx.config.manager as manager_module
from mdcx.config.manager import ConfigManager
from mdcx.config.models import Config


def _write_config(path: Path, modified: int) -> None:
    path.write_text(Config().model_dump_json(indent=2), encoding="utf-8")
    os.utime(path, (modified, modified))


def _redirect_manager_paths(monkeypatch, folder: Path) -> Path:
    mark_file = folder / "MDCx.config"
    monkeypatch.setattr(manager_module, "MAIN_PATH", folder)
    monkeypatch.setattr(manager_module, "MARK_FILE", mark_file)
    return mark_file


def test_missing_marked_config_recovers_latest_json(monkeypatch, tmp_path):
    mark_file = _redirect_manager_paths(monkeypatch, tmp_path)
    older = tmp_path / "older.json"
    latest = tmp_path / "latest.json"
    _write_config(older, 100)
    _write_config(latest, 200)
    mark_file.write_text(r"D:\moved-away\config.json", encoding="utf-8")

    recovered = ConfigManager()

    assert recovered.path == latest
    assert mark_file.read_text(encoding="utf-8") == str(latest)


def test_missing_marked_config_without_candidate_creates_local_default(monkeypatch, tmp_path):
    mark_file = _redirect_manager_paths(monkeypatch, tmp_path)
    mark_file.write_text(r"D:\moved-away\config.json", encoding="utf-8")

    recovered = ConfigManager()

    expected = tmp_path / "config.json"
    assert recovered.path == expected
    assert expected.is_file()
    assert Config.model_validate_json(expected.read_text(encoding="utf-8"))
    assert mark_file.read_text(encoding="utf-8") == str(expected)


def test_valid_marked_config_is_kept_even_if_local_json_is_newer(monkeypatch, tmp_path):
    mark_file = _redirect_manager_paths(monkeypatch, tmp_path)
    selected = tmp_path / "selected.json"
    newer = tmp_path / "newer.json"
    _write_config(selected, 100)
    _write_config(newer, 200)
    mark_file.write_text(str(selected), encoding="utf-8")

    recovered = ConfigManager()

    assert recovered.path == selected
    assert mark_file.read_text(encoding="utf-8") == str(selected)


def test_relative_marked_config_is_resolved_from_program_folder(monkeypatch, tmp_path):
    mark_file = _redirect_manager_paths(monkeypatch, tmp_path)
    selected = tmp_path / "portable.json"
    _write_config(selected, 100)
    mark_file.write_text(selected.name, encoding="utf-8")

    recovered = ConfigManager()

    assert recovered.path == selected
