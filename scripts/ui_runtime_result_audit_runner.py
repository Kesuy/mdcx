from __future__ import annotations

from pathlib import Path

from mdcx.models.flags import Flags

import ui_runtime_result_audit as audit


def _success_history(window, app, output: Path, report: dict) -> None:
    Flags.success_list = {
        Path(rf"D:\Media\Library\分类目录-{index:02d}\TEST-{index:04d} 这是用于滚动和长路径测试的已刮削成功文件名 2160p.mkv")
        for index in range(1, 31)
    }
    for width, height in audit.SIZES:
        audit._size(window, app, width, height)
        window.pushButton_view_success_file_clicked()
        app.processEvents()
        overlay = window.Ui.widget_show_success
        chain = []
        node = overlay
        while node is not None:
            chain.append(
                {
                    "name": node.objectName() or type(node).__name__,
                    "hidden": node.isHidden(),
                    "visible": node.isVisible(),
                }
            )
            node = node.parentWidget()
        report["checks"][f"success_overlay_{width}_chain"] = chain
        report["checks"][f"success_overlay_{width}_geometry"] = [
            overlay.x(), overlay.y(), overlay.width(), overlay.height()
        ]
        # show_responsive_overlay() must clear the overlay's own hidden state.
        # An ancestor can still be hidden when the widget belongs to a different
        # stacked page, which is why isVisible()/isVisibleTo(window) is too strict here.
        assert not overlay.isHidden()
        audit._render_widget(overlay, output / f"{width}x{height}-success-history-surface.jpg", quality=84)
        overlay.hide()
    lines = window.Ui.textBrowser_show_success_list.toPlainText().splitlines()
    scroll = window.Ui.textBrowser_show_success_list.verticalScrollBar()
    report["checks"]["success_history_count"] = len(Flags.success_list)
    report["checks"]["success_history_text_lines"] = len(lines)
    report["checks"]["success_history_scroll_max"] = scroll.maximum()
    assert len(lines) == 30
    assert scroll.maximum() > 0


audit._success_history = _success_history

if __name__ == "__main__":
    audit.main()
