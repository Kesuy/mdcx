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
        self.toggled = _Signal()

    def setEnabled(self, value):
        self.enabled = value

    def objectName(self):
        return "checkBox_force_avwiki_actor"

    def window(self):
        return SimpleNamespace(settings_controller=None)


class _Component:
    def setupUi(self, _container):
        self.checkBox_force_avwiki_actor = _ChildCheckBox()


class _Layout:
    def __init__(self):
        self.insertions = []

    def insertWidget(self, index, widget):
        self.insertions.append((index, widget))


def test_force_avwiki_option_is_defined_in_ui_source():
    ui_path = Path("mdcx/views/avwiki_actor_settings.ui")
    text = ui_path.read_text(encoding="utf-8")
    assert 'name="checkBox_force_avwiki_actor"' in text
    assert "↳ 强制使用 AV-Wiki（所有作品）" in text
    assert "仅在上级“使用 AV-Wiki 获取演员真实名字”开启时生效" in text


def test_force_avwiki_option_is_child_of_master_switch(monkeypatch):
    master = _MasterCheckBox()
    layout = _Layout()
    ui = SimpleNamespace(checkBox_actor_realname=master, horizontalLayout_8=layout)
    container = object()

    monkeypatch.setattr(module, "QWidget", lambda _parent: container)
    monkeypatch.setattr(module, "Ui_AvwikiActorSettings", _Component)

    child = module._ensure_force_avwiki_actor_checkbox(ui)

    assert layout.insertions == [(1, container)]
    assert child.enabled is False
    master.set_checked(True)
    assert child.enabled is True
    master.set_checked(False)
    assert child.enabled is False
