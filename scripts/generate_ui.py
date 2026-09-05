from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIEWS = ROOT / "mdcx" / "views"

UI_TARGETS = (
    (VIEWS / "MDCx.ui", VIEWS / "MDCx_shell.py"),
    (VIEWS / "posterCutTool.ui", VIEWS / "posterCutTool.py"),
    (VIEWS / "main_page.ui", VIEWS / "main_page.py"),
    (VIEWS / "log_page.ui", VIEWS / "log_page.py"),
    (VIEWS / "network_page.ui", VIEWS / "network_page.py"),
    (VIEWS / "tool_page.ui", VIEWS / "tool_page.py"),
    (VIEWS / "settings_page.ui", VIEWS / "settings_page.py"),
    (VIEWS / "about_page.ui", VIEWS / "about_page.py"),
    (VIEWS / "nfo_overlay.ui", VIEWS / "nfo_overlay.py"),
)


def generate() -> None:
    for ui_path, py_path in UI_TARGETS:
        subprocess.run(
            [sys.executable, "-m", "PyQt6.uic.pyuic", str(ui_path), "-o", str(py_path)],
            cwd=ROOT,
            check=True,
        )


def main() -> None:
    generate()


if __name__ == "__main__":
    main()
