from types import SimpleNamespace

from scripts.build import BuildManager


def test_windows_bundle_only_excludes_the_unused_opencv_video_plugin(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    spec = tmp_path / "MDCx.spec"
    spec.write_text("pyz = PYZ(a.pure)\n", encoding="utf-8")
    manager = BuildManager("MDCx", "4.0.14", create_dmg=False, debug=True)
    manager.is_windows = True
    manager.is_mac = False
    manager._modify_spec()
    keep = ["cv2/cv2.pyd", "cv2/config.py", "PyQt6/Qt6/bin/opengl32sw.dll", "av.libs/avcodec.dll"]
    binaries = [(name, "source", "BINARY") for name in keep + [r"cv2\opencv_videoio_ffmpeg4130_64.dll"]]
    analysis = SimpleNamespace(binaries=binaries, pure=[])
    exec(spec.read_text(encoding="utf-8"), {"a": analysis, "PYZ": lambda pure: pure})
    assert [item[0] for item in analysis.binaries] == keep
