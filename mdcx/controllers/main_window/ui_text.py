from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel


def set_elided_label_text(
    label: QLabel,
    text: str,
    *,
    mode: Qt.TextElideMode = Qt.TextElideMode.ElideMiddle,
) -> None:
    """按标签实际像素宽度显示文本，并在需要时保留首尾进行省略。"""

    normalized = str(text or "")
    label.setProperty("mdcxFullText", normalized)
    label.setToolTip(normalized)
    available_width = max(label.contentsRect().width(), 0)
    label.setText(label.fontMetrics().elidedText(normalized, mode, available_width))
