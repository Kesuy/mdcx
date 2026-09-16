from pathlib import Path
from types import SimpleNamespace

from mdcx.controllers.main_window import settings_composites as module


class _Signal:
    def __init__(self):
        self.callbacks = []

    def connect(self, callback):
        self.callbacks.append(callback)

    def emit(self, value):
        for callback in self.callbacks:
            callback(value)


class _MasterCheckBox:
    def __init__(self):
        self.checked = False
        self.toggled = _Signal()

    def isChecked(self):
        return self.checked

    def parentWidget(self):
        return object()

    def set_checked(self, value):
        self.checked = value
        self.toggled.emit(value)


class _ChildCheckBox:
    def __init__(self):
        self.enabled = None
        self.checked = False
        self.signals_blocked = False
        self.toggled = _Signal()

    def setEnabled(self, value):
        self.enabled = value

    def isChecked(self):
        return self.checked

    def setChecked(self, value):
        changed = self.checked != value
        self.checked = value
        if changed and not self.signals_blocked:
            self.toggled.emit(value)

    def blockSignals(self, value):
        previous = self.signals_blocked
        self.signals_blocked = value
        return previous

    def objectName(self):
        return "checkBox_force_avwiki_actor"

    def window(self):
        return SimpleNamespace(settings_controller=None)


class _Component:
    def setupUi(self, _container):
        self.checkBox_force_avwiki_actor = _ChildCheckBox()


class _HorizontalLayout:
    def __init__(self):
        self.insertions = []

    def insertWidget(self, index, widget):
        self.insertions.append((index, widget))


class _GridLayout:
    def __init__(self):
        self.removed = []
        self.additions = []

    def removeWidget(self, widget):
        self.removed.append(widget)

    def addWidget(self, widget, row, column, row_span, column_span):
        self.additions.append((widget, row, column, row_span, column_span))


def test_force_avwiki_option_is_defined_in_ui_source():
    ui_path = Path("mdcx/views/avwiki_actor_settings.ui")
    text = ui_path.read_text(encoding="utf-8")
    assert 'name="checkBox_force_avwiki_actor"' in text
    assert "强制使用 AV-Wiki（所有作品）" in text
    assert "↳" not in text
    assert "<number>24</number>" in text
    assert "仅在上级“使用 AV-Wiki 获取演员真实名字”开启时生效" in text


def test_force_avwiki_option_uses_separate_indented_child_row(monkeypatch):
    master = _MasterCheckBox()
    horizontal_layout = _HorizontalLayout()
    grid_layout = _GridLayout()
    help_label = object()
    ui = SimpleNamespace(
        checkBox_actor_realname=master,
        horizontalLayout_8=horizontal_layout,
        gridLayout_50=grid_layout,
        label_249=help_label,
    )
    container = object()
    monkeypatch.setattr(module, "QWidget", lambda _parent: container)
    monkeypatch.setattr(module, "Ui_AvwikiActorSettings", _Component)

    child = module._ensure_force_avwiki_actor_checkbox(ui)

    assert horizontal_layout.insertions == []
    assert grid_layout.removed == [help_label]
    assert grid_layout.additions == [
        (container, 2, 1, 1, 1),
        (help_label, 3, 1, 1, 1),
    ]
    assert child.enabled is False
    assert child.checked is False

    master.set_checked(True)
    assert child.enabled is True
    child.setChecked(True)
    assert child.checked is True

    master.set_checked(False)
    assert child.enabled is False
    assert child.checked is False


def test_force_avwiki_option_keeps_inline_fallback_for_legacy_ui(monkeypatch):
    master = _MasterCheckBox()
    horizontal_layout = _HorizontalLayout()
    ui = SimpleNamespace(checkBox_actor_realname=master, horizontalLayout_8=horizontal_layout)
    container = object()
    monkeypatch.setattr(module, "QWidget", lambda _parent: container)
    monkeypatch.setattr(module, "Ui_AvwikiActorSettings", _Component)

    child = module._ensure_force_avwiki_actor_checkbox(ui)

    assert horizontal_layout.insertions == [(1, container)]
    assert child.enabled is False
    assert child.checked is False
