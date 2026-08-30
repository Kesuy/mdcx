from types import SimpleNamespace

from mdcx.controllers.main_window import tool_controller
from mdcx.controllers.main_window.tool_controller import ToolController


def test_actor_action_saves_config_before_opening_log_and_submitting(monkeypatch):
    events = []
    window = SimpleNamespace(
        pushButton_save_config_clicked=lambda: events.append("save"),
        pushButton_show_log_clicked=lambda: events.append("log"),
    )
    controller = ToolController(window)
    task = object()

    monkeypatch.setattr(tool_controller, "update_emby_actor_info", lambda: events.append("create") or task)
    monkeypatch.setattr(
        tool_controller,
        "executor",
        SimpleNamespace(submit=lambda submitted: events.append(("submit", submitted))),
    )

    controller.update_actor_info()

    assert events == ["save", "log", "create", ("submit", task)]


def test_kodi_delete_preserves_no_save_behavior(monkeypatch):
    events = []
    window = SimpleNamespace(
        pushButton_save_config_clicked=lambda: events.append("save"),
        pushButton_show_log_clicked=lambda: events.append("log"),
    )
    controller = ToolController(window)
    task = object()

    monkeypatch.setattr(tool_controller, "creat_kodi_actors", lambda create: events.append(create) or task)
    monkeypatch.setattr(
        tool_controller,
        "executor",
        SimpleNamespace(submit=lambda submitted: events.append(("submit", submitted))),
    )

    controller.update_kodi_actors(False)

    assert events == ["log", False, ("submit", task)]


def test_actor_list_captures_selected_type_before_submitting(monkeypatch):
    submitted = []
    window = SimpleNamespace(
        Ui=SimpleNamespace(comboBox_pic_actor=SimpleNamespace(currentIndex=lambda: 3)),
        pushButton_show_log_clicked=lambda: None,
    )
    controller = ToolController(window)
    monkeypatch.setattr(tool_controller, "show_emby_actor_list", lambda actor_type: ("actor-list", actor_type))
    monkeypatch.setattr(tool_controller, "executor", SimpleNamespace(submit=submitted.append))

    controller.show_actor_list()

    assert submitted == [("actor-list", 3)]


def test_missing_number_check_does_not_resave_unchanged_library(monkeypatch):
    events = []
    ui = SimpleNamespace(
        pushButton_find_missing_number=SimpleNamespace(isEnabled=lambda: True),
        lineEdit_actors_name=SimpleNamespace(text=lambda: tool_controller.manager.config.actors_name),
        lineEdit_local_library_path=SimpleNamespace(
            text=lambda: ",".join(tool_controller.manager.config.local_library)
        ),
    )
    window = SimpleNamespace(
        Ui=ui,
        pushButton_save_config_clicked=lambda: events.append("save"),
        pushButton_show_log_clicked=lambda: events.append("log"),
    )
    controller = ToolController(window)
    monkeypatch.setattr(tool_controller, "check_missing_number", lambda show_dialog: ("missing", show_dialog))
    monkeypatch.setattr(
        tool_controller,
        "executor",
        SimpleNamespace(submit=lambda task: events.append(("submit", task))),
    )

    controller.find_missing_numbers(True)

    assert events == ["log", ("submit", ("missing", True))]
