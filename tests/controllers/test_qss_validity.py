from pathlib import Path

CONTROLLER_DIR = Path(__file__).parents[2] / "mdcx" / "controllers"


def test_controller_qss_has_valid_padding_and_pressed_selectors():
    qss_sources = (
        CONTROLLER_DIR / "cut_window.py",
        CONTROLLER_DIR / "main_window" / "style.py",
    )

    for source_path in qss_sources:
        source = source_path.read_text(encoding="utf-8")
        assert "padding: 2px, 2px" not in source
        assert ",pressed#" not in source
        assert ":press#" not in source
