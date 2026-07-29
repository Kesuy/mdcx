import os
import subprocess
import sys
from pathlib import Path


def _run_import_probe(code: str) -> list[str]:
    env = os.environ.copy()
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
    result = subprocess.run(
        [sys.executable, "-c", code],
        check=True,
        capture_output=True,
        env=env,
        text=True,
        timeout=10,
    )
    return result.stdout.splitlines()


def test_importing_entrypoint_does_not_start_ui_or_load_business_tree():
    loaded = _run_import_probe(
        "import sys; import main; "
        "print('mdcx.controllers.main_window.main_window' in sys.modules); "
        "print('mdcx.utils.video' in sys.modules); "
        "print('PIL.ImageFile' in sys.modules)"
    )

    assert loaded == ["False", "False", "False"]


def test_entrypoint_does_not_create_a_splash_screen():
    entrypoint = Path(__file__).parents[1] / "main.py"

    assert "QSplashScreen" not in entrypoint.read_text(encoding="utf-8")


def test_config_initialization_does_not_import_openai_sdk():
    loaded = _run_import_probe(
        "import sys; from mdcx.config.manager import manager; "
        "print('openai' in sys.modules); print(manager.computed.llm_client.initialized)"
    )

    assert loaded == ["False", "False"]


def test_llm_client_initializes_openai_sdk_on_first_access():
    loaded = _run_import_probe(
        "import sys; from mdcx.config.manager import manager; "
        "client = manager.computed.llm_client; print(client.initialized); "
        "print(type(client.client).__name__); "
        "print(client.initialized); print('openai' in sys.modules)"
    )

    assert loaded == ["False", "AsyncOpenAI", "True", "True"]


def test_scraper_image_helpers_do_not_import_opencv_until_face_crop_is_used():
    loaded = _run_import_probe("import sys; import mdcx.core.image; print('cv2' in sys.modules)")

    assert loaded == ["False"]
