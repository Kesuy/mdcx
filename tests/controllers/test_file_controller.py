from pathlib import Path
from types import SimpleNamespace

from mdcx.controllers.main_window import file_controller
from mdcx.controllers.main_window.file_controller import (
    FileController,
    FileFailureCategory,
    FileOperationKind,
    classify_file_failure,
)


def test_delete_folder_plan_is_a_side_effect_free_deduplicated_preview(tmp_path: Path):
    folder = tmp_path / "movie"
    plan = FileController.build_plan(
        FileOperationKind.DELETE_FOLDERS,
        [folder, folder],
        source_count=2,
        deduplicate=True,
    )

    assert plan.targets == (folder,)
    assert plan.source_count == 2
    assert not folder.exists()
    text = plan.confirmation_text()
    assert "操作预演（尚未修改文件）" in text
    assert "来源于 2 个选中项" in text
    assert str(folder) in text


def test_plan_preview_limits_long_target_lists():
    plan = FileController.build_plan(
        FileOperationKind.DELETE_FILES,
        [Path(f"movie-{index}.mp4") for index in range(10)],
    )

    assert "movie-0.mp4" in plan.preview(limit=3)
    assert "movie-3.mp4" not in plan.preview(limit=3)
    assert "其余 7 项省略" in plan.preview(limit=3)


def test_file_failure_classification_explains_retryability():
    privilege = classify_file_failure("OSError: [WinError 1314] A required privilege is not held by the client")
    cross_device = classify_file_failure("OSError: [WinError 17] different disk drive")
    missing = classify_file_failure("FileNotFoundError: movie.mp4")

    assert privilege.category is FileFailureCategory.PERMISSION
    assert privilege.retryable is True
    assert "开发者模式" in privilege.suggestion
    assert cross_device.category is FileFailureCategory.CROSS_DEVICE
    assert cross_device.retryable is False
    assert "软链接" in cross_device.suggestion
    assert missing.category is FileFailureCategory.MISSING
    assert missing.retryable is False


def test_delete_folders_keeps_original_failure_for_classification(monkeypatch, tmp_path: Path):
    deleted = []

    def fake_rmtree(path: Path) -> None:
        if path.name == "missing":
            raise FileNotFoundError(path)
        if path.name == "denied":
            raise PermissionError("[WinError 5] Access is denied")
        deleted.append(path)

    monkeypatch.setattr(file_controller.shutil, "rmtree", fake_rmtree)
    monkeypatch.setattr(file_controller.signal_qt, "show_log_text", lambda *_args: None)
    targets = {
        tmp_path / "ok": ["ok-item"],
        tmp_path / "missing": ["missing-item"],
        tmp_path / "denied": ["denied-item"],
    }

    success_count, success_names, failures, failed_targets = FileController.delete_folders(targets)

    assert deleted == [tmp_path / "ok"]
    assert success_count == 2
    assert success_names == ["ok-item", "missing-item"]
    assert list(failed_targets) == [tmp_path / "denied"]
    assert classify_file_failure(failures[0][1]).category is FileFailureCategory.PERMISSION


def test_create_links_previews_targets_before_mutation(monkeypatch, tmp_path: Path):
    source = tmp_path / "movie.mp4"
    output = tmp_path / "links"
    created = []
    window = SimpleNamespace()
    controller = FileController(window)
    plans = []

    monkeypatch.setattr(controller, "confirm_plan", lambda plan, **_kwargs: plans.append(plan) or True)
    monkeypatch.setattr(file_controller, "resolve_link_source_sync", lambda path: (True, path, ""))
    monkeypatch.setattr(file_controller, "resolve_success_record_source_sync", lambda path: (True, path, ""))
    monkeypatch.setattr(
        file_controller,
        "create_symlink_sync",
        lambda source_path, target_path: created.append((source_path, target_path)) or (True, ""),
    )
    monkeypatch.setattr(file_controller.signal_qt, "show_log_text", lambda *_args: None)
    monkeypatch.setattr(file_controller.signal_qt, "show_scrape_info", lambda *_args: None)

    controller.create_links(
        "soft",
        link_targets=[("movie", source)],
        output_dir=output,
        should_record_success=False,
    )

    assert plans[0].kind is FileOperationKind.CREATE_SYMLINKS
    assert plans[0].targets == (output / "movie.mp4",)
    assert created == [(source, output / "movie.mp4")]


def test_create_links_retry_only_reprocesses_failed_sources(monkeypatch, tmp_path: Path):
    source = tmp_path / "movie.mp4"
    output = tmp_path / "links"
    feedback = []
    window = SimpleNamespace(_show_action_failure_feedback=lambda *args, **kwargs: feedback.append((args, kwargs)))
    controller = FileController(window)
    attempts = []

    monkeypatch.setattr(file_controller, "resolve_link_source_sync", lambda path: (True, path, ""))
    monkeypatch.setattr(file_controller, "resolve_success_record_source_sync", lambda path: (True, path, ""))

    def create_link(source_path: Path, target_path: Path):
        attempts.append((source_path, target_path))
        return (False, "PermissionError: access is denied") if len(attempts) == 1 else (True, "")

    monkeypatch.setattr(file_controller, "create_symlink_sync", create_link)
    monkeypatch.setattr(file_controller.signal_qt, "show_log_text", lambda *_args: None)
    monkeypatch.setattr(file_controller.signal_qt, "show_scrape_info", lambda *_args: None)

    controller.create_links(
        "soft",
        link_targets=[("movie", source)],
        output_dir=output,
        should_record_success=False,
        show_plan=False,
    )

    assert len(feedback) == 1
    feedback[0][1]["retry_callback"]()
    assert attempts == [(source, output / "movie.mp4"), (source, output / "movie.mp4")]
