from __future__ import annotations

import os
import time
import traceback
import webbrowser
from typing import TYPE_CHECKING, cast

from PyQt6.QtCore import QEvent, Qt, QTimer
from PyQt6.QtGui import QCursor, QGuiApplication
from PyQt6.QtWidgets import QComboBox, QMessageBox, QPushButton, QSystemTrayIcon

from mdcx.base.web import check_theporndb_api_token
from mdcx.config.enums import Switch
from mdcx.config.manager import manager
from mdcx.consts import GITHUB_ISSUES_URL, GITHUB_RELEASES_URL, IS_WINDOWS
from mdcx.signals import signal_qt
from mdcx.tools.actress_db import ActressDB
from mdcx.versioning import is_newer_version

from .responsive_layout import apply_responsive_layout
from .site_priority_dialog import apply_site_priority_theme
from .style import apply_application_palette, build_sidebar_background_style, build_sidebar_button_style

if TYPE_CHECKING:
    from PyQt6.QtGui import QMouseEvent


class WindowLifecycleMixin:
    def tray_icon_click(self, e):
        if e == QSystemTrayIcon.ActivationReason.Trigger and IS_WINDOWS:
            if self.isVisible():
                self.hide()
            else:
                self.activateWindow()
                self.raise_()
                self.show()

    def tray_icon_show(self):
        if self.windowState() & Qt.WindowState.WindowMinimized:  # 最小化时恢复
            self.showNormal()
        self.recover_windowflags()  # 恢复焦点
        self.activateWindow()
        self.raise_()
        self.show()

    def change_mainpage(self, t):
        self.pushButton_main_clicked()

    def eventFilter(self, a0, a1):
        if (
            isinstance(a0, QComboBox)
            and a0.property("wheelRequiresFocus")
            and a1.type() == QEvent.Type.Wheel
            and not a0.hasFocus()
        ):
            a1.ignore()
            return True

        # print(event.type())

        if a1.type() == QEvent.Type.MouseButtonRelease:  # 松开鼠标，检查是否在前台
            self.recover_windowflags()
        if a1.type() == QEvent.Type.ApplicationActivate and not self.isVisible():
            self.show()
        if a0 is self.Ui.label_number and a1.type() == QEvent.Type.MouseButtonRelease:
            a1 = cast("QMouseEvent", a1)
            if a1.button() == Qt.MouseButton.LeftButton and self._main_source_url:
                webbrowser.open(self._main_source_url)
                return True
        if a0.objectName() == "label_poster" or a0.objectName() == "label_thumb":
            if a1.type() == QEvent.Type.MouseButtonPress:
                a1 = cast("QMouseEvent", a1)
                if a1.button() == Qt.MouseButton.LeftButton:
                    self.start_click_time = time.time()
                    self.start_click_pos = a1.globalPosition().toPoint()
            elif a1.type() == QEvent.Type.MouseButtonRelease:
                a1 = cast("QMouseEvent", a1)
                if a1.button() == Qt.MouseButton.LeftButton:
                    if not bool(a1.globalPosition().toPoint() - self.start_click_pos) or (
                        time.time() - self.start_click_time < 0.05
                    ):
                        self._pic_main_clicked()
        if a0 is self.Ui.textBrowser_log_main.viewport() or a0 is self.Ui.textBrowser_log_main_2.viewport():
            if not self.Ui.textBrowser_log_main_3.isHidden() and a1.type() == QEvent.Type.MouseButtonPress:
                self.Ui.textBrowser_log_main_3.hide()
                self.Ui.pushButton_scraper_failed_list.hide()
                self.Ui.pushButton_save_failed_list.hide()
        return super().eventFilter(a0, a1)

    def showEvent(self, a0):
        super().showEvent(a0)
        apply_responsive_layout(self)

    def resizeEvent(self, a0):
        super().resizeEvent(a0)
        if hasattr(self, "Ui") and hasattr(self, "_resize_grip"):
            apply_responsive_layout(self)

    def changeEvent(self, a0):
        # self.show_traceback_log(QEvent.WindowStateChange)
        # WindowState （WindowNoState=0 正常窗口; WindowMinimized= 1 最小化;
        # WindowMaximized= 2 最大化; WindowFullScreen= 3 全屏;WindowActive= 8 可编辑。）
        # windows平台无问题，仅mac平台python版有问题
        if (
            not IS_WINDOWS
            and self.window_radius
            and a0.type() == QEvent.Type.WindowStateChange
            and self.windowState() == Qt.WindowState.WindowNoState
        ):
            self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)  # 隐藏边框
            self.show()

    def closeEvent(self, a0):
        self.ready_to_exit()
        if a0:
            a0.ignore()

    def _windows_auto_adjust(self):
        if manager.config.window_title == "hide":  # 隐藏标题栏
            if self.window_radius == 0:
                self.show_flag = True
            self.window_radius = 5
            if IS_WINDOWS:
                self.window_border = 1
            else:
                self.window_border = 0
            self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)  # 隐藏标题栏
            self.Ui.pushButton_close.setVisible(True)
            self.Ui.pushButton_min.setVisible(True)
            self.Ui.widget_buttons.move(0, 50)

        else:  # 显示标题栏
            if self.window_radius == 5:
                self.show_flag = True
            self.window_radius = 0
            self.window_border = 0
            self.window_marjin = 0
            self.setWindowFlag(Qt.WindowType.FramelessWindowHint, False)  # 显示标题栏
            self.Ui.pushButton_close.setVisible(False)
            self.Ui.pushButton_min.setVisible(False)
            self.Ui.widget_buttons.move(0, 20)

        if bool(self.dark_mode != self.Ui.checkBox_dark_mode.isChecked()):
            self.show_flag = True
            self.dark_mode = self.Ui.checkBox_dark_mode.isChecked()

        if self.show_flag:
            self.show_flag = False
            self.set_style()  # 样式美化
            apply_site_priority_theme(self)

            # self.setWindowState(Qt.WindowNoState)                               # 恢复正常窗口
            self.show()
            self._change_page()

    def _change_page(self):
        page = int(self.Ui.stackedWidget.currentIndex())
        if page == 0:
            self.pushButton_main_clicked()
        elif page == 1:
            self.pushButton_show_log_clicked()
        elif page == 2:
            self.pushButton_show_net_clicked()
        elif page == 3:
            self.pushButton_tool_clicked()
        elif page == 4:
            self.pushButton_setting_clicked()
        elif page == 5:
            self.pushButton_about_clicked()

    def _bind_system_theme_refresh(self) -> None:
        try:
            QGuiApplication.styleHints().colorSchemeChanged.connect(
                lambda *_args: apply_application_palette(self.dark_mode)
            )
        except Exception:
            pass

    def mousePressEvent(self, a0):
        if a0 and a0.button() == Qt.MouseButton.LeftButton:
            self.m_drag = True
            self.m_DragPosition = a0.globalPosition().toPoint() - self.pos()
            self.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))  # 按下左键改变鼠标指针样式为手掌

    def mouseReleaseEvent(self, a0):
        if a0 and a0.button() == Qt.MouseButton.LeftButton:
            self.m_drag = False
            self.m_DragPosition = None
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))  # 释放左键改变鼠标指针样式为箭头

    def mouseMoveEvent(self, a0):
        if a0 and self.m_drag and self.m_DragPosition is not None and a0.buttons() & Qt.MouseButton.LeftButton:
            self.move(a0.globalPosition().toPoint() - self.m_DragPosition)
            a0.accept()
        else:
            self.m_drag = False
            self.m_DragPosition = None
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

    def pushButton_close_clicked(self):
        if Switch.HIDE_CLOSE in manager.config.switch_on:
            self.hide()
        else:
            self.ready_to_exit()

    def ready_to_exit(self):
        if Switch.SHOW_DIALOG_EXIT in manager.config.switch_on:
            if not self.isVisible():
                self.show()
            if self.windowState() & Qt.WindowState.WindowMinimized:
                self.showNormal()

            # print(self.window().isActiveWindow()) # 是否为活动窗口
            self.raise_()
            box = QMessageBox(QMessageBox.Icon.Warning, "退出", "确定要退出吗？")
            box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            box.button(QMessageBox.StandardButton.Yes).setText("退出 MDCx")
            box.button(QMessageBox.StandardButton.No).setText("取消")
            box.setDefaultButton(QMessageBox.StandardButton.No)
            reply = box.exec()
            if reply != QMessageBox.StandardButton.Yes:
                self.raise_()
                self.show()
                return
        self.exit_app()

    def exit_app(self):
        show_poster = manager.config.show_poster
        switch_on = manager.config.switch_on
        need_save_config = False

        if self.Ui.checkBox_cover.isChecked() != show_poster:
            manager.config.show_poster = self.Ui.checkBox_cover.isChecked()
            need_save_config = True
        if self.Ui.textBrowser_log_main_2.isHidden() == (Switch.SHOW_LOGS in switch_on):
            if self.Ui.textBrowser_log_main_2.isHidden():
                manager.config.switch_on.remove(Switch.SHOW_LOGS)
            else:
                manager.config.switch_on.append(Switch.SHOW_LOGS)
            need_save_config = True
        if need_save_config:
            try:
                manager.save()
            except Exception:
                signal_qt.show_traceback_log(traceback.format_exc())
        if hasattr(self, "preview_image_loader"):
            self.preview_image_loader.shutdown()
        if hasattr(self, "tray_icon"):
            self.tray_icon.hide()
        self.task_manager.shutdown()
        manager.shutdown()
        signal_qt.show_traceback_log("\n\n\n\n************ 程序正常退出！************\n")
        os._exit(0)

    def pushButton_min_clicked(self):
        if Switch.HIDE_MINI in manager.config.switch_on:
            self.hide()
            return
        # mac 平台 python 版本 最小化有问题，此处就是为了兼容它，需要先设置为显示窗口标题栏才能最小化
        if not IS_WINDOWS:
            self.setWindowFlag(Qt.WindowType.FramelessWindowHint, False)  # 不隐藏边框

        # self.setWindowState(Qt.WindowState.WindowMinimized)
        # self.show_traceback_log(self.isMinimized())
        self.showMinimized()

    def pushButton_min_clicked2(self):
        if not IS_WINDOWS:
            self.setWindowFlag(Qt.WindowType.FramelessWindowHint, False)  # 不隐藏边框
            # self.show()  # 加上后可以显示缩小动画
        self.showMinimized()

    def set_left_button_style(self):
        try:
            self.Ui.left_backgroud_widget.setStyleSheet(
                build_sidebar_background_style(self.dark_mode, self.window_radius)
            )
            for button in (
                self.Ui.pushButton_main,
                self.Ui.pushButton_log,
                self.Ui.pushButton_net,
                self.Ui.pushButton_tool,
                self.Ui.pushButton_setting,
                self.Ui.pushButton_about,
            ):
                button.setStyleSheet(build_sidebar_button_style(button.objectName(), self.dark_mode))
        except Exception:
            signal_qt.show_traceback_log(traceback.format_exc())

    def _apply_sidebar_selection(self, button: QPushButton) -> None:
        self.set_left_button_style()
        button.setStyleSheet(build_sidebar_button_style(button.objectName(), self.dark_mode, active=True))

    def show_version(self):
        try:
            self.task_manager.submit_sync(
                "version-check",
                self._load_version_info,
                on_success=self._apply_version_info,
                on_error=lambda error: signal_qt.show_traceback_log(error),
            )
        except Exception:
            signal_qt.show_traceback_log(traceback.format_exc())
            signal_qt.show_log_text(traceback.format_exc())

    def _load_version_info(self) -> str:
        # Resolve through the historical public module so integrations that
        # patch this symbol keep working after responsibility extraction.
        from .main_window import check_version as current_check_version

        latest_version = current_check_version()
        if manager.config.use_database:
            ActressDB.init_db()
        return latest_version or ""

    def _apply_version_info(self, latest_version: str) -> None:
        version_info = f"基于 MDC-GUI 修改 当前版本: {self.localversion}"
        download_link = ""
        if latest_version:
            if is_newer_version(latest_version, self.localversion):
                self.new_version = f"\n🍉 有新版本了！（{latest_version}）"
                signal_qt.show_scrape_info()
                self.Ui.label_show_version.setCursor(Qt.CursorShape.OpenHandCursor)  # 设置鼠标形状为十字形
                version_info = f'基于 MDC-GUI 修改 · 当前版本: {self.localversion} （ <font color="red" >最新版本是: {latest_version}，请及时更新！🚀 </font>）'
                download_link = f' ⬇️ <a href="{GITHUB_RELEASES_URL}">下载新版本</a>'
            else:
                version_info = f'基于 MDC-GUI 修改 · 当前版本: {self.localversion} （ <font color="green">你使用的是最新版本！🎉 </font>）'

        feedback = f' 💌 问题反馈: <a href="{GITHUB_ISSUES_URL}">GitHub Issues</a>'

        # 显示版本信息和反馈入口
        signal_qt.show_log_text(version_info)
        if feedback or download_link:
            self.main_logs_show.emit(f"{feedback}{download_link}")
        signal_qt.show_log_text("================================================================================")
        self.task_manager.submit_sync(
            "check-theporndb-token",
            check_theporndb_api_token,
            on_error=lambda error: signal_qt.show_traceback_log(error),
        )

    def _show_version_thread(self):
        """Compatibility wrapper for lightweight callers; production uses callbacks."""
        latest_version = WindowLifecycleMixin._load_version_info(self)
        WindowLifecycleMixin._apply_version_info(self, latest_version)

    def label_version_clicked(self, ev):
        try:
            webbrowser.open(GITHUB_RELEASES_URL)
        except Exception:
            signal_qt.show_traceback_log(traceback.format_exc())

    def pushButton_main_clicked(self):
        self.Ui.stackedWidget.setCurrentIndex(0)
        self._apply_sidebar_selection(self.Ui.pushButton_main)

    def pushButton_show_log_clicked(self):
        self.Ui.stackedWidget.setCurrentIndex(1)
        self._apply_sidebar_selection(self.Ui.pushButton_log)

    def pushButton_tool_clicked(self):
        self.Ui.stackedWidget.setCurrentIndex(3)
        self._apply_sidebar_selection(self.Ui.pushButton_tool)
        self._reset_tool_scroll_position()
        QTimer.singleShot(0, self._reset_tool_scroll_position)
        QTimer.singleShot(50, self._reset_tool_scroll_position)

    def _reset_tool_scroll_position(self):
        scroll_area = self.Ui.scrollArea_10
        scroll_bar = scroll_area.verticalScrollBar()
        scroll_bar.setValue(scroll_bar.minimum())
        scroll_area.ensureVisible(0, 0, 0, 0)

    def pushButton_setting_clicked(self):
        self.Ui.stackedWidget.setCurrentIndex(4)
        self._apply_sidebar_selection(self.Ui.pushButton_setting)
        try:
            self._check_mac_config_folder()
        except Exception:
            signal_qt.show_traceback_log(traceback.format_exc())

    def pushButton_show_net_clicked(self):
        self.Ui.stackedWidget.setCurrentIndex(2)
        self._apply_sidebar_selection(self.Ui.pushButton_net)

    def pushButton_about_clicked(self):
        self.Ui.stackedWidget.setCurrentIndex(5)
        self._apply_sidebar_selection(self.Ui.pushButton_about)
