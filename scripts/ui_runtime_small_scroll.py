from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("MDCX_OFFLINE", "1")

from PyQt6.QtWidgets import QApplication, QScrollArea

from mdcx.controllers.main_window.main_window import MyMAinWindow
from mdcx.controllers.main_window.responsive_layout import apply_responsive_layout
from ui_runtime_audit import _configure_cjk_font, _patch_runtime_side_effects, _render_widget


def main() -> None:
    output = Path("ui-audit/windows-small-scroll")
    output.mkdir(parents=True, exist_ok=True)
    _patch_runtime_side_effects()
    app = QApplication.instance() or QApplication([])
    _configure_cjk_font(app)
    window = MyMAinWindow()
    window.show()
    app.processEvents()
    if not getattr(window, "_startup_finished", False):
        window._finish_startup()
    app.processEvents()

    stack = window.Ui.stackedWidget
    stack.setCurrentWidget(window.Ui.page_setting)
    tabs = window.Ui.tabWidget
    for width, height in ((880, 700), (1100, 760)):
        window.resize(width, height)
        apply_responsive_layout(window)
        app.processEvents()
        for index in range(tabs.count()):
            tabs.setCurrentIndex(index)
            apply_responsive_layout(window)
            app.processEvents()
            for scroll in tabs.currentWidget().findChildren(QScrollArea):
                if not scroll.isVisibleTo(window) or scroll.widget() is None:
                    continue
                content = scroll.widget()
                filename = f"{width}x{height}-tab-{index:02d}-{scroll.objectName()}.jpg"
                _render_widget(content, output / filename, quality=78)

    for timer_name in ("timer", "timer_scrape", "timer_update", "timer_remain_task"):
        timer = getattr(window, timer_name, None)
        if timer is not None:
            timer.stop()
    window.hide()
    window.deleteLater()
    app.processEvents()


if __name__ == "__main__":
    main()
