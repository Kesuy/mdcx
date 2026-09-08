#!/usr/bin/env python3
import platform
import sys

_QT_TRANSLATOR = None


def install_qt_translations(app) -> bool:
    """Load Qt's Chinese strings for standard menus and dialogs."""

    global _QT_TRANSLATOR
    from PyQt6.QtCore import QLibraryInfo, QTranslator

    translator = QTranslator(app)
    translations_path = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    if not translator.load("qtbase_zh_CN", translations_path):
        return False
    app.installTranslator(translator)
    _QT_TRANSLATOR = translator
    return True


def show_constants():
    """显示所有运行时常量"""
    from mdcx.consts import IS_DOCKER, IS_MAC, IS_NFC, IS_PYINSTALLER, IS_WINDOWS, MAIN_PATH
    from mdcx.utils.video import VIDEO_BACKEND

    constants = {
        "MAIN_PATH": MAIN_PATH,
        "IS_WINDOWS": IS_WINDOWS,
        "IS_MAC": IS_MAC,
        "IS_DOCKER": IS_DOCKER,
        "IS_NFC": IS_NFC,
        "IS_PYINSTALLER": IS_PYINSTALLER,
        "VIDEO_BACKEND": VIDEO_BACKEND,
    }
    print("Run time constants:")
    for key, value in constants.items():
        print(f"\t{key}: {value}")


def run(argv: list[str] | None = None) -> int:
    effective_argv = sys.argv if argv is None else argv
    smoke_home = None
    if "--smoke-test-ui" in effective_argv:
        import os
        import tempfile
        from pathlib import Path

        import mdcx.consts as consts

        smoke_home = tempfile.TemporaryDirectory(prefix="mdcx-ui-smoke-")
        consts.MAIN_PATH = Path(smoke_home.name)
        consts.MARK_FILE = consts.MAIN_PATH / "MDCx.config"
        if not getattr(sys, "frozen", False):
            import shutil

            shutil.copytree(
                Path(__file__).resolve().parent / "resources",
                consts.MAIN_PATH / "resources",
                ignore=shutil.ignore_patterns("fonts"),
            )
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        os.environ["MDCX_OFFLINE"] = "1"
        from mdcx.config.secrets import secret_store

        secret_store.available = lambda: False

    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QIcon
    from PyQt6.QtWidgets import QApplication

    # Qt 6 使用 logical pixel；明确保留 125%/150% 等非整数缩放，避免固定布局被取整放大。
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    app = QApplication(effective_argv)
    install_qt_translations(app)
    app.setStyle("Fusion")
    if platform.system() != "Windows":
        app.setWindowIcon(QIcon("resources/Img/MDCx.ico"))  # 设置任务栏图标

    # QApplication 建立后再加载业务树和可选媒体后端，保留延迟导入带来的启动优化。
    from PIL import ImageFile

    from mdcx.controllers.main_window.main_window import MyMAinWindow
    from mdcx.controllers.main_window.style import apply_application_palette

    ImageFile.LOAD_TRUNCATED_IMAGES = True
    apply_application_palette(False)

    # The build pipeline invokes this mode against the frozen artifact. It
    # validates Qt DLL loading and the complete startup import tree without
    # opening a window or entering the event loop.
    if "--smoke-test" in effective_argv:
        print("MDCx frozen startup smoke test passed")
        return 0

    if smoke_home is not None:
        import time

        from mdcx.config.resources import resources

        if not getattr(sys, "frozen", False):
            resources._resources_base = Path(__file__).resolve().parent / "resources"
        MyMAinWindow.show_version = lambda self: None
        MyMAinWindow.auto_start = lambda self: None
        started = time.perf_counter()
        ui = MyMAinWindow()
        ui.show()
        app.processEvents()
        print(f"MDCx first screen: {time.perf_counter() - started:.3f}s", flush=True)
        assert hasattr(ui.Ui, "tabWidget")
        assert resources.actor_mapping_data is not None
        ui.change_buttons_status()
        ui.reset_buttons_status()
        assert ui.Ui.comboBox_fixed_scraping_type.currentText()
        from PyQt6.QtWidgets import QComboBox

        assert all(combo.currentText().strip() for combo in ui.Ui.page_setting.findChildren(QComboBox))
        ui.pushButton_setting_clicked()
        for page_index in range(ui.Ui.tabWidget.count()):
            ui.Ui.tabWidget.setCurrentIndex(page_index)
            app.processEvents()
        for combo in (ui.Ui.comboBox_website_all, ui.Ui.comboBox_fixed_scraping_type):
            for page_index in range(ui.Ui.tabWidget.count()):
                if ui.Ui.tabWidget.widget(page_index).isAncestorOf(combo):
                    ui.Ui.tabWidget.setCurrentIndex(page_index)
            from PyQt6.QtWidgets import QScrollArea

            for area in ui.Ui.tabWidget.currentWidget().findChildren(QScrollArea):
                if area.isAncestorOf(combo):
                    area.ensureWidgetVisible(combo)
            app.processEvents()
            combo.showPopup()
            app.processEvents()
            assert combo.view().viewport().height() >= combo.view().sizeHintForRow(0)
            screenshot_dir = os.environ.get("MDCX_SMOKE_SCREENSHOT_DIR")
            if screenshot_dir:
                combo.view().window().grab().save(str(Path(screenshot_dir) / f"{combo.objectName()}.png"))
            combo.hidePopup()
        print("MDCx settings tabs and expanded popups passed", flush=True)
        crop_window = ui._get_cutwindow()
        import cv2
        import numpy as np

        assert cv2.resize(np.zeros((8, 8, 3), dtype=np.uint8), (4, 4)).shape == (4, 4, 3)
        assert cv2.barcode_BarcodeDetector() is not None
        assert hasattr(cv2, "FaceDetectorYN")
        model_path = os.environ.get("MDCX_SMOKE_FACE_MODEL")
        if model_path:
            detector = cv2.FaceDetectorYN.create(model_path, "", (320, 320))
            detector.detect(np.zeros((320, 320, 3), dtype=np.uint8))
            from mdcx.core import face_crop

            face_crop._face_model_path = lambda: Path(model_path)
            print("MDCx frozen YuNet inference passed", flush=True)
        from PIL import Image

        sample_path = Path(smoke_home.name) / "SMOKE-001.jpg"
        Image.new("RGB", (800, 450), "navy").save(sample_path)
        crop_window.showimage(sample_path)
        assert not crop_window.Ui.pushButton_auto_face.isEnabled()
        deadline = time.monotonic() + 10
        while not crop_window.Ui.pushButton_auto_face.isEnabled() and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(0.01)
        assert crop_window.Ui.pushButton_auto_face.isEnabled()
        assert crop_window.Ui.label_crop_status.text().startswith(("未检测到有效人脸", "已定位人脸"))
        print("MDCx automatic face detection on image load passed", flush=True)
        ui.task_manager.shutdown()
        ui.hide()
        from mdcx.models.flags import Flags

        if Flags.log_txt is not None:
            Flags.log_txt.close()
            Flags.log_txt = None
        print("MDCx frozen UI and OpenCV smoke test passed", flush=True)
        smoke_home.cleanup()
        return 0

    show_constants()

    ui = MyMAinWindow()
    ui.show()
    app.installEventFilter(ui)
    try:
        return app.exec()
    except Exception as e:
        print(e)
        return 1


if __name__ == "__main__":
    sys.exit(run())
