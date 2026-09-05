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
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QIcon
    from PyQt6.QtWidgets import QApplication

    # Qt 6 使用 logical pixel；明确保留 125%/150% 等非整数缩放，避免固定布局被取整放大。
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    effective_argv = sys.argv if argv is None else argv
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
