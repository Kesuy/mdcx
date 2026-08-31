from __future__ import annotations

import html
from pathlib import Path

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtGui import QAction, QIcon, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
)

from mdcx.config.resources import resources
from mdcx.core.naming import NameRenderOptions, NamingTarget, render_name
from mdcx.models.types import CrawlersResult, FileInfo
from mdcx.utils import split_path

from .style import build_menu_style, set_semantic_property


class PageSetupMixin:
    def _setup_name_template_preview(self) -> None:
        self.Ui.plainTextEdit_name_template_preview.setPlainText(
            self.Ui.lineEdit_media_name.text()
            or "{{ number }}{% if studio %} [{{ studio }}]{% endif %} {{ originaltitle }}"
        )
        self.Ui.plainTextEdit_name_template_preview.textChanged.connect(self._update_name_template_preview)
        self._update_name_template_preview()

    def _build_name_preview_sample(self) -> tuple[FileInfo, CrawlersResult]:
        file_info = FileInfo.empty()
        file_info.number = "ABC-123"
        file_info.file_path = Path("D:/Media/Input/ABC-123.mp4")
        file_info.folder_path = file_info.file_path.parent
        file_info.file_name = "ABC-123"
        file_info.definition = "4K"
        file_info.c_word = "-中字"
        file_info.wuma = "-无码"

        result = CrawlersResult.empty()
        result.number = "ABC-123"
        result.title = "中文标题"
        result.originaltitle = "Original Title"
        result.actors = ["演员A", "演员B"]
        result.all_actors = ["演员A", "演员B", "男演员C"]
        result.directors = ["导演A"]
        result.series = "系列A"
        result.studio = "Studio A"
        result.publisher = "发行商A"
        result.release = "2024-01-02"
        result.runtime = "120"
        result.mosaic = "有码"
        result.letters = "ABC"
        result.wanted = "123"
        result.score = "4.5"
        result.outline = "示例简介"
        return file_info, result

    def _update_name_template_preview(self) -> None:
        template = self.Ui.plainTextEdit_name_template_preview.toPlainText()
        if not template.strip():
            set_semantic_property(self.Ui.label_name_template_preview_result, "statusRole", "neutral")
            self.Ui.label_name_template_preview_result.setText("状态：等待输入模板")
            return
        try:
            file_info, result = self._build_name_preview_sample()
            rendered = render_name(
                template,
                file_info,
                result,
                NameRenderOptions(
                    target=NamingTarget.FILE,
                    show_definition_suffix=False,
                    show_cnword_suffix=False,
                    show_moword_suffix=False,
                    max_length=120,
                ),
            )
        except Exception as exc:
            set_semantic_property(self.Ui.label_name_template_preview_result, "statusRole", "danger")
            self.Ui.label_name_template_preview_result.setText("状态：语法错误\n" + html.escape(str(exc), quote=False))
            return

        set_semantic_property(self.Ui.label_name_template_preview_result, "statusRole", "success")
        self.Ui.label_name_template_preview_result.setText(
            "状态：语法正确\n"
            f"结果：{html.escape(rendered.text, quote=False)}\n"
            "示例字段：number=ABC-123, studio=Studio A, originaltitle=Original Title, definition=4K"
        )

    def _setup_fc2ppvdb_cookie_ui(self):
        def move_grid_item(item, row: int, column: int):
            index = self.Ui.gridLayout_10.indexOf(item)
            layout_item = self.Ui.gridLayout_10.takeAt(index)
            if layout_item.widget() is not None:
                self.Ui.gridLayout_10.addWidget(layout_item.widget(), row, column, 1, 1)
            else:
                self.Ui.gridLayout_10.addLayout(layout_item.layout(), row, column, 1, 1)

        move_grid_item(self.Ui.label_45, 1, 0)
        move_grid_item(self.Ui.plainTextEdit_cookie_javdb, 1, 1)
        move_grid_item(self.Ui.horizontalLayout_151, 2, 1)
        move_grid_item(self.Ui.label_425, 5, 0)
        move_grid_item(self.Ui.plainTextEdit_cookie_javbus, 5, 1)
        move_grid_item(self.Ui.horizontalLayout_152, 6, 1)

        def add_section_title(name: str, text: str, row: int, *, separated: bool = False):
            label = QLabel(text, self.Ui.gridLayoutWidget_10)
            label.setObjectName(name)
            label.setProperty("sectionTitle", True)
            label.setProperty("sectionSeparated", separated)
            self.Ui.gridLayout_10.addWidget(label, row, 0, 1, 2)
            return label

        self.Ui.label_javdb_cookie_section = add_section_title("label_javdb_cookie_section", "JavDB", 0)
        self.Ui.label_javbus_cookie_section = add_section_title(
            "label_javbus_cookie_section", "JavBus", 4, separated=True
        )
        self.Ui.label_fc2cmadb_cookie_section = add_section_title(
            "label_fc2cmadb_cookie_section", "FC2CMADB", 8, separated=True
        )

        self.Ui.label_fc2ppvdb_cookie = QLabel(self.Ui.gridLayoutWidget_10)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.Ui.label_fc2ppvdb_cookie.sizePolicy().hasHeightForWidth())
        self.Ui.label_fc2ppvdb_cookie.setSizePolicy(sizePolicy)
        self.Ui.label_fc2ppvdb_cookie.setMinimumSize(130, 30)
        self.Ui.label_fc2ppvdb_cookie.setMaximumSize(130, 16777215)
        self.Ui.label_fc2ppvdb_cookie.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.Ui.label_fc2ppvdb_cookie.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTrailing | Qt.AlignmentFlag.AlignVCenter
        )
        self.Ui.label_fc2ppvdb_cookie.setText("fc2cmadb：\n（登录状态）")
        self.Ui.label_fc2ppvdb_cookie.setObjectName("label_fc2ppvdb_cookie")
        self.Ui.gridLayout_10.addWidget(self.Ui.label_fc2ppvdb_cookie, 9, 0, 1, 1)

        self.Ui.plainTextEdit_cookie_fc2ppvdb = QPlainTextEdit(self.Ui.gridLayoutWidget_10)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.Ui.plainTextEdit_cookie_fc2ppvdb.sizePolicy().hasHeightForWidth())
        self.Ui.plainTextEdit_cookie_fc2ppvdb.setSizePolicy(sizePolicy)
        self.Ui.plainTextEdit_cookie_fc2ppvdb.setMinimumWidth(400)
        self.Ui.plainTextEdit_cookie_fc2ppvdb.setProperty("cookieEditor", True)
        self.Ui.plainTextEdit_cookie_fc2ppvdb.setPlaceholderText(
            "登录 fc2cmadb 后，从浏览器开发者工具的 Request Headers 复制完整 Cookie（不要填写账号密码）"
        )
        self.Ui.plainTextEdit_cookie_fc2ppvdb.setObjectName("plainTextEdit_cookie_fc2ppvdb")
        self.Ui.gridLayout_10.addWidget(self.Ui.plainTextEdit_cookie_fc2ppvdb, 9, 1, 1, 1)

        self.Ui.horizontalLayout_fc2ppvdb_cookie = QHBoxLayout()
        self.Ui.horizontalLayout_fc2ppvdb_cookie.setObjectName("horizontalLayout_fc2ppvdb_cookie")
        self.Ui.pushButton_check_fc2ppvdb_cookie = QPushButton(self.Ui.gridLayoutWidget_10)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.Ui.pushButton_check_fc2ppvdb_cookie.sizePolicy().hasHeightForWidth())
        self.Ui.pushButton_check_fc2ppvdb_cookie.setSizePolicy(sizePolicy)
        self.Ui.pushButton_check_fc2ppvdb_cookie.setText("检查cookie")
        self.Ui.pushButton_check_fc2ppvdb_cookie.setToolTip("验证登录后才能访问的影片，过期 Cookie 不会保存")
        self.Ui.pushButton_check_fc2ppvdb_cookie.setObjectName("pushButton_check_fc2ppvdb_cookie")
        self.Ui.horizontalLayout_fc2ppvdb_cookie.addWidget(self.Ui.pushButton_check_fc2ppvdb_cookie)

        self.Ui.label_fc2ppvdb_cookie_result = QLabel(self.Ui.gridLayoutWidget_10)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.Ui.label_fc2ppvdb_cookie_result.sizePolicy().hasHeightForWidth())
        self.Ui.label_fc2ppvdb_cookie_result.setSizePolicy(sizePolicy)
        self.Ui.label_fc2ppvdb_cookie_result.setMinimumSize(0, 0)
        self.Ui.label_fc2ppvdb_cookie_result.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.Ui.label_fc2ppvdb_cookie_result.setText("")
        self.Ui.label_fc2ppvdb_cookie_result.setAlignment(
            Qt.AlignmentFlag.AlignLeading | Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self.Ui.label_fc2ppvdb_cookie_result.setObjectName("label_fc2ppvdb_cookie_result")
        self.Ui.horizontalLayout_fc2ppvdb_cookie.addWidget(self.Ui.label_fc2ppvdb_cookie_result)
        self.Ui.gridLayout_10.addLayout(self.Ui.horizontalLayout_fc2ppvdb_cookie, 10, 1, 1, 1)

        for editor in (
            self.Ui.plainTextEdit_cookie_javdb,
            self.Ui.plainTextEdit_cookie_javbus,
            self.Ui.plainTextEdit_cookie_fc2ppvdb,
        ):
            editor.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            editor.setMinimumHeight(56)
            editor.setMaximumHeight(56)

        self.Ui.gridLayoutWidget_10.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.Ui.label_75.setWordWrap(True)
        self.Ui.label_75.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.Ui.groupBox_10.layout().activate()

    def _setup_baidu_translate_ui(self):
        self.Ui.label_60.setText("填写 DeepL API / DeepLX URL / 百度 API 凭据后，才会生效；未填写时会自动跳过。")
        self.Ui.label_601.setText("填写 DeepL API / DeepLX URL / 百度 API 凭据后，才会生效；未填写时会自动跳过。")

        self.Ui.checkBox_baidu = QCheckBox(self.Ui.layoutWidget_2)
        self.Ui.checkBox_baidu.setMinimumSize(self.Ui.checkBox_google.minimumSize())
        self.Ui.checkBox_baidu.setObjectName("checkBox_baidu")
        self.Ui.checkBox_baidu.setText("百度")
        self.Ui.horizontalLayout_20.addWidget(self.Ui.checkBox_baidu)

        self.Ui.label_baidu_appid = QLabel(self.Ui.layoutWidget_2)
        self.Ui.label_baidu_appid.setMinimumSize(self.Ui.label_80.minimumSize())
        self.Ui.label_baidu_appid.setLayoutDirection(self.Ui.label_80.layoutDirection())
        self.Ui.label_baidu_appid.setFrameShape(self.Ui.label_80.frameShape())
        self.Ui.label_baidu_appid.setAlignment(self.Ui.label_80.alignment())
        self.Ui.label_baidu_appid.setObjectName("label_baidu_appid")
        self.Ui.label_baidu_appid.setText("百度 APP ID：")
        self.Ui.gridLayout_32.addWidget(self.Ui.label_baidu_appid, 5, 0, 1, 1)

        self.Ui.lineEdit_baidu_appid = QLineEdit(self.Ui.layoutWidget_2)
        self.Ui.lineEdit_baidu_appid.setMinimumSize(self.Ui.lineEdit_deepl_key.minimumSize())
        self.Ui.lineEdit_baidu_appid.setProperty("semanticRole", "input")
        self.Ui.lineEdit_baidu_appid.setObjectName("lineEdit_baidu_appid")
        self.Ui.gridLayout_32.addWidget(self.Ui.lineEdit_baidu_appid, 5, 1, 1, 1)

        self.Ui.label_baidu_key = QLabel(self.Ui.layoutWidget_2)
        self.Ui.label_baidu_key.setMinimumSize(self.Ui.label_80.minimumSize())
        self.Ui.label_baidu_key.setLayoutDirection(self.Ui.label_80.layoutDirection())
        self.Ui.label_baidu_key.setFrameShape(self.Ui.label_80.frameShape())
        self.Ui.label_baidu_key.setAlignment(self.Ui.label_80.alignment())
        self.Ui.label_baidu_key.setObjectName("label_baidu_key")
        self.Ui.label_baidu_key.setText("百度密钥：")
        self.Ui.gridLayout_32.addWidget(self.Ui.label_baidu_key, 6, 0, 1, 1)

        self.Ui.lineEdit_baidu_key = QLineEdit(self.Ui.layoutWidget_2)
        self.Ui.lineEdit_baidu_key.setMinimumSize(self.Ui.lineEdit_deepl_key.minimumSize())
        self.Ui.lineEdit_baidu_key.setProperty("semanticRole", "input")
        self.Ui.lineEdit_baidu_key.setObjectName("lineEdit_baidu_key")
        self.Ui.gridLayout_32.addWidget(self.Ui.lineEdit_baidu_key, 6, 1, 1, 1)

        self.Ui.layoutWidget_2.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

    def Init_Ui(self): ...

    def Init_Singal(self): ...

    def Init_QSystemTrayIcon(self): ...

    def init_QTreeWidget(self): ...

    def load_config(self): ...

    def creat_right_menu(self):
        self.menu_start = QAction(QIcon(resources.start_icon), "  开始刮削\tCtrl+R", self)
        self.menu_stop = QAction(QIcon(resources.stop_icon), "  停止刮削\tCtrl+R", self)
        self.menu_number = QAction(QIcon(resources.input_number_icon), "  重新刮削\tCtrl+F", self)
        self.menu_website = QAction(QIcon(resources.input_website_icon), "  输入网址重新刮削\tCtrl+L", self)
        self.menu_del_file = QAction(QIcon(resources.del_file_icon), "  删除文件\tDelete", self)
        self.menu_del_folder = QAction(QIcon(resources.del_folder_icon), "  删除文件和文件夹\tShift+Delete", self)
        self.menu_make_symlink = QAction(QIcon(resources.open_folder_icon), "  在指定位置创建软链接", self)
        self.menu_make_symlink_in_dir = QAction(
            QIcon(resources.open_folder_icon), "  在指定位置创建软链接（按文件名建目录）", self
        )
        self.menu_make_hardlink = QAction(QIcon(resources.open_folder_icon), "  在指定位置创建硬链接", self)
        self.menu_make_hardlink_in_dir = QAction(
            QIcon(resources.open_folder_icon), "  在指定位置创建硬链接（按文件名建目录）", self
        )
        self.menu_folder = QAction(QIcon(resources.open_folder_icon), "  打开文件夹\tCtrl+O", self)
        self.menu_nfo = QAction(QIcon(resources.open_nfo_icon), "  编辑 NFO\tCtrl+E", self)
        self.menu_play = QAction(QIcon(resources.play_icon), "  播放\tCtrl+P", self)
        self.menu_hide = QAction(QIcon(resources.hide_boss_icon), "  隐藏\tCtrl+H", self)

        self.menu_start.triggered.connect(self.pushButton_start_scrape_clicked)
        self.menu_stop.triggered.connect(self.pushButton_start_scrape_clicked)
        self.menu_number.triggered.connect(self.search_by_number_clicked)
        self.menu_website.triggered.connect(self.search_by_url_clicked)
        self.menu_del_file.triggered.connect(self.main_del_file_click)
        self.menu_del_folder.triggered.connect(self.main_del_folder_click)
        self.menu_make_symlink.triggered.connect(self.main_make_symlink_click)
        self.menu_make_symlink_in_dir.triggered.connect(self.main_make_symlink_in_dir_click)
        self.menu_make_hardlink.triggered.connect(self.main_make_hardlink_click)
        self.menu_make_hardlink_in_dir.triggered.connect(self.main_make_hardlink_in_dir_click)
        self.menu_folder.triggered.connect(self.main_open_folder_click)
        self.menu_nfo.triggered.connect(self.main_open_nfo_click)
        self.menu_play.triggered.connect(self.main_play_click)
        self.menu_hide.triggered.connect(self.hide)

        QShortcut(QKeySequence(self.tr("Ctrl+F")), self, self.search_by_number_clicked)
        QShortcut(QKeySequence(self.tr("Ctrl+L")), self, self.search_by_url_clicked)
        QShortcut(
            QKeySequence(self.tr("Delete")),
            self,
            lambda: self.main_del_file_click() if self.Ui.treeWidget_number.hasFocus() else None,
        )
        QShortcut(
            QKeySequence(self.tr("Shift+Delete")),
            self,
            lambda: self.main_del_folder_click() if self.Ui.treeWidget_number.hasFocus() else None,
        )
        QShortcut(QKeySequence(self.tr("Ctrl+O")), self, self.main_open_folder_click)
        QShortcut(QKeySequence(self.tr("Ctrl+E")), self, self.main_open_nfo_click)
        QShortcut(QKeySequence(self.tr("Ctrl+P")), self, self.main_play_click)
        QShortcut(QKeySequence(self.tr("Ctrl+R")), self, self.pushButton_start_scrape_clicked)
        QShortcut(QKeySequence(self.tr("Ctrl+H")), self, self.hide)
        # QShortcut(QKeySequence(self.tr("Esc")), self, self.hide)
        QShortcut(QKeySequence(self.tr("Ctrl+M")), self, self.pushButton_min_clicked2)
        QShortcut(QKeySequence(self.tr("Ctrl+W")), self, self.ready_to_exit)

        self.Ui.page_main.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.Ui.page_main.customContextMenuRequested.connect(self._menu)

    def _menu(self, pos=None):
        if not pos:
            pos = self.Ui.pushButton_right_menu.pos() + QPoint(40, 10)
            # pos = QCursor().pos()
        menu = QMenu()
        menu.setStyleSheet(build_menu_style(self.dark_mode))
        selected_entries = self._get_selected_entries()
        selected_entry = selected_entries[0] if len(selected_entries) == 1 else None
        if len(selected_entries) > 1:
            menu.addAction(QAction(f"已选择 {len(selected_entries)} 项", self))
            menu.addSeparator()
            menu.addAction(self.menu_nfo)
            menu.addSeparator()
            menu.addAction(self.menu_del_file)
            menu.addAction(self.menu_del_folder)
            menu.addAction(self.menu_make_symlink)
            menu.addAction(self.menu_make_symlink_in_dir)
            menu.addAction(self.menu_make_hardlink)
            menu.addAction(self.menu_make_hardlink_in_dir)
            menu.exec(self.Ui.page_main.mapToGlobal(pos))
            return

        if selected_entry is not None:
            _, _, _, file_path = selected_entry
            file_name = split_path(file_path)[1]
            menu.addAction(QAction(file_name, self))
            menu.addSeparator()
        elif self.file_main_open_path:
            file_name = split_path(self.file_main_open_path)[1]
            menu.addAction(QAction(file_name, self))
            menu.addSeparator()
        else:
            menu.addAction(QAction("请刮削后使用！", self))
            menu.addSeparator()
            if self.Ui.pushButton_start_cap.text() != "开始":
                menu.addAction(self.menu_stop)
            else:
                menu.addAction(self.menu_start)
        menu.addAction(self.menu_number)
        menu.addAction(self.menu_website)
        menu.addSeparator()
        menu.addAction(self.menu_del_file)
        menu.addAction(self.menu_del_folder)
        menu.addAction(self.menu_make_symlink)
        menu.addAction(self.menu_make_symlink_in_dir)
        menu.addAction(self.menu_make_hardlink)
        menu.addAction(self.menu_make_hardlink_in_dir)
        menu.addSeparator()
        menu.addAction(self.menu_folder)
        menu.addAction(self.menu_nfo)
        menu.addAction(self.menu_play)
        menu.addAction(self.menu_hide)
        menu.exec(self.Ui.page_main.mapToGlobal(pos))

    def _tree_result_context_menu(self, pos: QPoint):
        item = self.Ui.treeWidget_number.itemAt(pos)
        if item is not None and item.text(0) not in {"成功", "失败"}:
            self._set_result_item_as_current_selection(item)
        global_pos = self.Ui.treeWidget_number.viewport().mapToGlobal(pos)
        self._menu(self.Ui.page_main.mapFromGlobal(global_pos))

    def set_style(self): ...

    def set_dark_style(self): ...
