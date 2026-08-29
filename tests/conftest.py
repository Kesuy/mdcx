import asyncio
import os
import shutil
import tempfile
from pathlib import Path

import pytest

# Unit tests are deterministic and must never download optional runtime models.
os.environ.setdefault("MDCX_OFFLINE", "1")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# The test-only wheel provides a persistent, known-good FFmpeg without making
# its large binary part of the production import graph or frozen executable.
try:
    from imageio_ffmpeg import get_ffmpeg_exe

    os.environ.setdefault("MDCX_FFMPEG", get_ffmpeg_exe())
except (ImportError, RuntimeError):
    pass

if os.name == "nt":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


_SESSION_TEMP: Path | None = None


def pytest_configure(config: pytest.Config) -> None:
    """Use a fresh temp root so stale Windows ACLs cannot poison later runs."""
    global _SESSION_TEMP
    if config.option.basetemp is None:
        _SESSION_TEMP = Path(tempfile.mkdtemp(prefix=f"mdcx-pytest-{os.getpid()}-"))
        config.option.basetemp = str(_SESSION_TEMP)


def pytest_unconfigure(config: pytest.Config) -> None:
    del config
    if _SESSION_TEMP is not None:
        shutil.rmtree(_SESSION_TEMP, ignore_errors=True)
