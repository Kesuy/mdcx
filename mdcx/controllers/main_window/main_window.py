from __future__ import annotations

import threading
from collections import deque
from pathlib import Path
from typing import TYPE_CHECKING

from PyQt6.QtCore import QPoint, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog,
    QMainWindow,
    QSystemTrayIcon,
)

from mdcx.base.file import get_success_list, save_remain_list
from mdcx.base.web import check_version
from mdcx.config.resources import resources
from mdcx.consts import LOCAL_VERSION
from mdcx.image import PreviewImageLoader
from mdcx.models.types import CrawlersResult, ShowData
from mdcx.runtime import ApplicationServices
from mdcx.signals import signal_qt
from mdcx.task_manager import QtTaskManager
from mdcx.views.MDCx import Ui_MDCx

from .file_controller import FileController
from .handlers import show_netstatus
from .help_controller import HelpControllerMixin
from .init import Init_QSystemTrayIcon, Init_Singal, Init_Ui, init_QTreeWidget, install_result_tree_view
from .load_config import load_config
from .log_controller import LogControllerMixin
from .main_page_mixin import MainPageMixin
from .network_controller import NetworkController
from .nfo_controller import NfoController
from .page_setup_mixin import PageSetupMixin
from .preview_controller import PreviewControllerMixin
from .result_model import ResultItem
from .save_config import save_config
from .scrape_controller import ScrapeController
from .settings_page import SettingsPageController
from .settings_tool_slots import SettingsToolSlotsMixin
from .style import (
    set_dark_style,
    set_style,
)
from .tool_controller import ToolController
from .window_lifecycle import WindowLifecycleMixin

if TYPE_CHECKING:
    from ..cut_window import CutWindow


class MyMAinWindow(
    PageSetupMixin,
    MainPageMixin,
    SettingsToolSlotsMixin,
    WindowLifecycleMixin,
    PreviewControllerMixin,
    LogControllerMixin,
    HelpControllerMixin,
    QMainWindow,
):
    main_logs_show = pyqtSignal(str)  # 显示刮削日志信号
    main_logs_clear = pyqtSignal(str)  # 清空刮削日志信号
    req_logs_clear = pyqtSignal(str)  # 清空请求日志信号
    main_req_logs_show = pyqtSignal(str)  # 显示刮削后台日志信号
    net_logs_show = pyqtSignal(str)  # 显示网络检测日志信号
    set_javdb_cookie = pyqtSignal(str)  # 加载javdb cookie文本内容到设置页面
    set_javdb_status = pyqtSignal(str)  # javdb 检查状态更新
    set_fc2ppvdb_cookie = pyqtSignal(str)  # 加载 fc2cmadb Cookie 文本内容到设置页面
    set_fc2ppvdb_status = pyqtSignal(str)  # fc2ppvdb 检查状态更新
    set_javbus_cookie = pyqtSignal(str)  # 加载javbus cookie文本内容到设置页面
    set_javbus_status = pyqtSignal(str)  # javbus 检查状态更新
    exec_save_config = pyqtSignal()  # 主线程执行保存配置
    set_label_file_path = pyqtSignal(str)  # 主界面更新路径信息显示
    set_pic_pixmap = pyqtSignal(list, list)  # 主界面显示封面、缩略图
    set_pic_text = pyqtSignal(str)  # 主界面显示封面信息
    change_to_mainpage = pyqtSignal(str)  # 切换到主界面
    label_result = pyqtSignal(str)
    pushButton_start_cap = pyqtSignal(str)
    pushButton_start_cap2 = pyqtSignal(str)
    pushButton_start_single_file = pyqtSignal(str)
    pushButton_add_sub_for_all_video = pyqtSignal(str)
    pushButton_show_pic_actor = pyqtSignal(str)
    pushButton_add_actor_info = pyqtSignal(str)
    pushButton_add_actor_pic = pyqtSignal(str)
    pushButton_add_actor_pic_kodi = pyqtSignal(str)
    pushButton_del_actor_folder = pyqtSignal(str)
    pushButton_check_and_clean_files = pyqtSignal(str)
    pushButton_move_mp4 = pyqtSignal(str)
    pushButton_find_missing_number = pyqtSignal(str)
    label_show_version = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.task_manager = QtTaskManager(self)
        self.services = ApplicationServices.from_globals(task_manager=self.task_manager)

        # region 初始化需要的变量
        self.localversion = LOCAL_VERSION  # 当前版本号
        self.new_version = "\n🔍 点击检查最新版本"  # 有版本更新时在左下角显示的新版本信息
        self.show_data: ShowData | None = None  # 当前树状图选中文件的数据
        self.img_path = None  # 当前树状图选中文件的图片地址
        self.m_drag = False  # 允许鼠标拖动的标识
        self.m_DragPosition: QPoint | None = None  # 鼠标拖动位置
        self.logs_counts = 0  # 日志次数（每1w次清屏）
        self.req_logs_counts = 0  # 日志次数（每1w次清屏）
        self.main_log_queue: deque[str] = deque()
        self.main_log_batch_size = 80
        self.main_log_max_count = 10000
        self.file_main_open_path = Path()  # 主界面打开的文件路径
        self.json_array: dict[str, ShowData] = {}  # 主界面右侧结果树状数据
        self.preview_request_id = 0  # 主界面图片预览请求序号，用于丢弃过期加载结果
        self._main_source_url = ""  # 当前番号可打开的刮削来源详情页

        self.window_radius = 0  # 窗口四角弧度，为0时表示显示窗口标题栏
        self.window_border = 0  # 窗口描边，为0时表示显示窗口标题栏
        self.dark_mode = False  # 暗黑模式标识
        self.check_mac = True  # 检测配置目录
        # self.window_marjin = 0 窗口外边距，为0时不往里缩
        self.show_flag = True  # 是否加载刷新样式

        self.timer = QTimer()  # 初始化一个定时器，用于显示日志
        self.timer.timeout.connect(self.show_detail_log)
        self.timer.timeout.connect(self._flush_main_log_queue)
        self.timer.start(100)  # 设置间隔100毫秒
        self.timer_scrape = QTimer()  # 初始化一个定时器，用于间隔刮削
        self.timer_scrape.timeout.connect(self.auto_scrape)
        self.timer_update = QTimer()  # 初始化一个定时器，用于检查更新
        self.timer_update.timeout.connect(check_version)
        self.timer_update.start(43200000)  # 设置检查间隔12小时
        self.timer_remain_task = QTimer()  # 初始化一个定时器，用于显示保存剩余任务
        self.timer_remain_task.timeout.connect(save_remain_list)
        self.timer_remain_task.start(1500)  # 设置间隔1.5秒
        self.atuo_scrape_count = 0  # 循环刮削次数
        # endregion

        # region 其它属性声明
        self.threads_list: list[threading.Thread] = []  # 启动的线程列表
        self._thread_stop_event = threading.Event()
        self.start_click_time = 0
        self.start_click_pos: QPoint
        self.window_marjin = None
        self.now_show_name = None
        self._nfo_batch_show_names: list[str] = []
        self._nfo_dirty_fields: set[str] = set()
        self._nfo_editor_loading = False
        self._nfo_diff_confirmation_enabled = True
        self.show_name = None
        self.options: QFileDialog.Option
        self.tray_icon: QSystemTrayIcon
        self.item_succ: ResultItem
        self.item_fail: ResultItem
        # endregion

        # region 初始化 UI
        resources.get_fonts()
        self.Ui = Ui_MDCx()  # 实例化 Ui
        self.Ui.setupUi(self)  # 初始化 Ui
        self.file_controller = FileController(self)
        self.network_controller = NetworkController(self)
        self.nfo_controller = NfoController(self)
        self.scrape_controller = ScrapeController(self)
        self.tool_controller = ToolController(self)
        self._bind_system_theme_refresh()
        self._setup_fc2ppvdb_cookie_ui()
        self._setup_baidu_translate_ui()
        self.settings_controller = SettingsPageController(self)
        # 裁切窗口依赖图片处理和文件识别模块，仅在用户首次打开裁切功能时加载。
        self.cutwindow: CutWindow | None = None
        self.preview_image_loader = PreviewImageLoader(self)
        self.preview_image_loader.loaded.connect(self._apply_preview_images)
        # Replace the generated tree before Init_Singal. Connecting first would
        # leave mouse/selection handlers attached to the deleted QTreeWidget.
        install_result_tree_view(self)
        self.Init_Singal()  # 信号连接
        self.Init_Ui()  # 设置Ui初始状态
        self.load_config()  # 加载配置
        # 先让构造函数返回并显示主窗口，再在事件循环空闲时完成非关键初始化。
        # 这会缩短双击 EXE 到首屏可见的时间，同时保持原有启动行为。
        QTimer.singleShot(0, self._finish_startup)
        # endregion

    def _finish_startup(self) -> None:
        if getattr(self, "_startup_finished", False):
            return
        self._startup_finished = True
        self._setup_name_template_preview()
        get_success_list()  # 获取历史成功刮削列表

        # region 启动显示信息和后台检查更新
        self.show_scrape_info()  # 主界面左下角显示一些配置信息
        self.show_net_info("\n🏠 代理设置在:【设置】 - 【网络】 - 【代理设置】。")
        show_netstatus()  # 检查网络界面显示当前网络代理信息
        self.show_net_info(
            "\n💡 Cloudflare Bypass：在【设置】-【网络】-【CF Bypass】填写本地服务地址后生效，"
            "例如 http://127.0.0.1:8000。\n"
            "▶️ 点击右上角 【开始检测】按钮以测试网络连通性。"
        )
        signal_qt.add_log("🍯 你可以点击左下角的图标来 显示 / 隐藏 请求信息面板！")
        self.show_version()  # 日志页面显示版本信息
        self.creat_right_menu()  # 加载右键菜单
        self.pushButton_main_clicked()  # 切换到主界面
        self.auto_start()  # 自动开始刮削
        # endregion

    def _get_cutwindow(self) -> CutWindow:
        if self.cutwindow is None:
            from ..cut_window import CutWindow

            self.cutwindow = CutWindow(self)
        return self.cutwindow

    def _get_nfo_controller(self) -> NfoController:
        controller = vars(self).get("nfo_controller")
        if controller is None:
            controller = NfoController(self)
            self.nfo_controller = controller
        return controller

    def _get_file_controller(self) -> FileController:
        controller = vars(self).get("file_controller")
        if controller is None:
            controller = FileController(self)
            self.file_controller = controller
        return controller

    def _get_scrape_controller(self) -> ScrapeController:
        controller = vars(self).get("scrape_controller")
        if controller is None:
            controller = ScrapeController(self)
            self.scrape_controller = controller
        return controller

    def _get_tool_controller(self) -> ToolController:
        controller = vars(self).get("tool_controller")
        if controller is None:
            controller = ToolController(self)
            self.tool_controller = controller
        return controller

        # menu.move(pos)
        # menu.show()

        # self.Ui.treeWidget_number.verticalScrollBar().setValue(self.Ui.treeWidget_number.verticalScrollBar().maximum())
        # self.Ui.treeWidget_number.setCurrentItem(node)
        # self.Ui.treeWidget_number.scrollToItem(node)

    @staticmethod
    def _apply_nfo_editor_patch(data: CrawlersResult, patch: dict[str, str]) -> None:
        NfoController.apply_patch(data, patch)

    def _show_nfo_info(self, selected_show_data: list[ShowData] | None = None):
        self._get_nfo_controller().show(selected_show_data)

    def _save_batch_nfo_info(self) -> None:
        self._get_nfo_controller().save_batch()

    def _find_related_cd_entries(self, show_data: ShowData, old_number: str) -> list[ShowData]:
        return self._get_nfo_controller().find_related_cd_entries(show_data, old_number)

    def _save_nfo_entry(
        self,
        show_data: ShowData,
        original_current_data: CrawlersResult,
    ) -> tuple[bool, list[ShowData]]:
        return self._get_nfo_controller().save_entry(show_data, original_current_data)

    def save_nfo_info(self) -> bool:
        return self._get_nfo_controller().save()

        # self.Ui.lineEdit_movie_number.setText('')


# region 外部方法定义
MyMAinWindow.load_config = load_config
MyMAinWindow.save_config = save_config
MyMAinWindow.Init_QSystemTrayIcon = Init_QSystemTrayIcon
MyMAinWindow.Init_Ui = Init_Ui
MyMAinWindow.Init_Singal = Init_Singal
MyMAinWindow.init_QTreeWidget = init_QTreeWidget
MyMAinWindow.set_style = set_style
MyMAinWindow.set_dark_style = set_dark_style
# endregion
