import threading
from asyncio import Event
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypedDict

if TYPE_CHECKING:
    from .failure import FailureRecord
    from .session import ScrapeSession

from .enums import FileMode
from .types import ScrapeResult


class FileDoneDict(TypedDict):
    poster: Path | None
    thumb: Path | None
    fanart: Path | None
    trailer: Path | None
    local_poster: Path | None
    local_thumb: Path | None
    local_fanart: Path | None
    local_trailer: Path | None


@dataclass
class _Flags:
    # 指定刮削 #todo 改为传参
    appoint_url: str = ""
    website_name: str = ""

    # 刮削相关
    rest_time_convert: int = 0
    rest_time_convert_: int = 0
    total_kills: int = 0
    now_kill: int = 0
    success_save_time: float = 0.0
    next_start_time: float = 0.0
    count_claw: int = 0  # 批量刮削次数
    can_save_remain: bool = False  # 保存剩余任务
    remain_list: list[Path] = field(default_factory=list)
    _remain_lock: Any = field(default_factory=threading.RLock, repr=False)
    _remain_version: int = field(default=0, repr=False)
    new_again_dic: dict[Path, tuple[str, str, str]] = field(default_factory=dict)
    again_dic: dict[Path, tuple[str, str, str]] = field(default_factory=dict)  # 待重新刮削的字典
    start_time: float = 0.0
    file_mode: FileMode = FileMode.Default  # 默认刮削待刮削目录
    counting_order: int = 0  # 刮削顺序
    _total_count: int = 0  # 未绑定 session 时的兼容总数
    rest_now_begin_count: int = 0  # 本轮刮削开始统计的线程序号（实际-1）
    sleep_end: Event = field(default_factory=Event)  # 本轮休眠标识
    rest_next_begin_time: float = 0.0  # 下一轮开始时间
    scrape_starting: int = 0  # 已进入过刮削流程的数量
    _scrape_started: int = 0  # 未绑定 session 时的兼容计数
    _scrape_done: int = 0
    _succ_count: int = 0
    _fail_count: int = 0
    # 所有文件最终输出路径的字典（如已存在，则视为重复文件，直接跳过）
    file_new_path_dic: dict[Path, list[Path]] = field(default_factory=dict)
    # 当前文件的图片最终输出路径的字典（如已存在，则最终图片文件视为已处理过）
    pic_catch_set: set[Path] = field(default_factory=set)
    # 当前番号的图片已下载完成的标识（如已存在，视为图片已下载完成）
    file_done_dic: dict[str, FileDoneDict] = field(default_factory=dict)
    # 当前文件夹剧照已处理的标识（如已存在，视为剧照已处理过）
    extrafanart_deal_set: set[Path] = field(default_factory=set)
    # 当前文件trailer已处理的标识（如已存在，视为剧照已处理过）
    trailer_deal_set: set[Path] = field(default_factory=set)
    # 当前文件夹剧照已下载的标识（如已存在，视为剧照已处理过）
    theme_videos_deal_set: set[Path] = field(default_factory=set)
    # 当前文件nfo已处理的标识（如已存在，视为剧照已处理过）
    nfo_deal_set: set[Path] = field(default_factory=set)
    # 去获取json的番号列表
    json_get_set: set[str] = field(default_factory=set)
    # 番号的json刮削状态（None: 进行中，True: 成功，False: 失败）
    json_get_status: dict[str, bool | None] = field(default_factory=dict)
    # 获取成功的json
    json_data_dic: dict[str, ScrapeResult] = field(default_factory=dict)
    img_path: str = ""
    # 失败文件及其错误原因
    failed_list: list[tuple[Path, str]] = field(default_factory=list)
    failed_records: list["FailureRecord"] = field(default_factory=list)
    session: "ScrapeSession | None" = field(default=None, repr=False)
    scrape_start_time: float = 0.0
    success_list: set[Path] = field(default_factory=set)
    stop_other: bool = True  # 非刮削线程停止标识
    stop_requested: bool = False  # 手动停止刮削请求标识

    def replace_remain_list(self, paths: list[Path], *, mark_dirty: bool = True) -> None:
        if self.session is not None:
            self.session.replace_remain_queue(paths, mark_dirty=mark_dirty)
            self.remain_list = self.session.state.remain_queue
            self.can_save_remain = mark_dirty
            return
        with self._remain_lock:
            self.remain_list = list(paths)
            self._remain_version += 1
            self.can_save_remain = mark_dirty

    def remove_remain_path(self, path: Path) -> bool:
        if self.session is not None:
            removed = self.session.remove_remain_path(path)
            self.can_save_remain = self.session.remain_snapshot()[2]
            return removed
        with self._remain_lock:
            try:
                self.remain_list.remove(path)
            except ValueError:
                return False
            self._remain_version += 1
            self.can_save_remain = True
            return True

    def remain_snapshot(self) -> tuple[list[Path], int, bool]:
        if self.session is not None:
            return self.session.remain_snapshot()
        with self._remain_lock:
            return list(self.remain_list), self._remain_version, self.can_save_remain

    def mark_remain_saved(self, version: int) -> None:
        if self.session is not None:
            self.session.mark_remain_saved(version)
            self.can_save_remain = self.session.remain_snapshot()[2]
            return
        with self._remain_lock:
            if self._remain_version == version:
                self.can_save_remain = False

    # show
    log_txt: Any = None  # 日志文件对象
    scrape_like_text: str = ""
    main_mode_text: str = ""

    single_file_path: Path = field(default_factory=Path)  # 工具-单文件刮削的文件路径

    # for missing
    actor_numbers_dic: dict[str, list[str]] = field(default_factory=dict)  # 每个演员所有番号的字典
    local_number_set: set[str] = field(default_factory=set)  # 本地所有番号的集合
    local_number_cnword_set: set[str] = field(default_factory=set)  # 本地所有有字幕的番号的集合

    def _get_progress(self, state_name: str, legacy_name: str) -> int:
        if self.session is not None:
            return int(getattr(self.session.state, state_name))
        return int(getattr(self, legacy_name))

    def _set_progress(self, state_name: str, legacy_name: str, value: int) -> None:
        normalized = int(value)
        if self.session is not None:
            setattr(self.session.state, state_name, normalized)
        setattr(self, legacy_name, normalized)

    @property
    def total_count(self) -> int:
        return self._get_progress("total_count", "_total_count")

    @total_count.setter
    def total_count(self, value: int) -> None:
        self._set_progress("total_count", "_total_count", value)

    @property
    def scrape_started(self) -> int:
        return self._get_progress("started_count", "_scrape_started")

    @scrape_started.setter
    def scrape_started(self, value: int) -> None:
        self._set_progress("started_count", "_scrape_started", value)

    @property
    def scrape_done(self) -> int:
        return self._get_progress("completed_count", "_scrape_done")

    @scrape_done.setter
    def scrape_done(self, value: int) -> None:
        self._set_progress("completed_count", "_scrape_done", value)

    @property
    def succ_count(self) -> int:
        return self._get_progress("success_count", "_succ_count")

    @succ_count.setter
    def succ_count(self, value: int) -> None:
        self._set_progress("success_count", "_succ_count", value)

    @property
    def fail_count(self) -> int:
        return self._get_progress("failure_count", "_fail_count")

    @fail_count.setter
    def fail_count(self, value: int) -> None:
        self._set_progress("failure_count", "_fail_count", value)

    def reset(self) -> None:
        self.session = None
        self.failed_list = []
        self.failed_records = []
        self.counting_order = 0
        self.total_count = 0
        self.rest_now_begin_count = 0
        self.sleep_end.set()  # 初始状态为未休眠
        self.scrape_starting = 0
        self.scrape_started = 0
        self.scrape_done = 0
        self.succ_count = 0
        self.fail_count = 0
        self.file_new_path_dic = {}
        self.pic_catch_set = set()
        self.file_done_dic = {}
        self.extrafanart_deal_set = set()
        self.trailer_deal_set = set()
        self.theme_videos_deal_set = set()
        self.nfo_deal_set = set()
        self.json_get_set = set()
        self.json_get_status = {}
        self.json_data_dic = {}
        self.img_path = ""
        self.stop_requested = False

    def bind_session(self, session: "ScrapeSession") -> None:
        """Expose the active per-run state to legacy callers during migration."""
        self.session = session
        self.remain_list = session.state.remain_queue
        self.failed_records = session.state.failures
        self.json_data_dic = session.scrape_results
        self.again_dic = session.state.retry_context
        self.file_new_path_dic = session.cache("file_new_path_dic")
        self.pic_catch_set = session.cache("pic_catch_set", set)
        self.file_done_dic = session.cache("file_done_dic")
        self.extrafanart_deal_set = session.cache("extrafanart_deal_set", set)
        self.trailer_deal_set = session.cache("trailer_deal_set", set)
        self.theme_videos_deal_set = session.cache("theme_videos_deal_set", set)
        self.nfo_deal_set = session.cache("nfo_deal_set", set)
        self.json_get_set = session.cache("json_get_set", set)
        self.json_get_status = session.cache("json_get_status")
        self.sync_progress_from_session()

    def sync_progress_from_session(self) -> None:
        """Mirror session-owned counters for legacy UI and helper readers."""
        if self.session is None:
            return
        state = self.session.state
        self.file_mode = state.file_mode
        self._total_count = state.total_count
        self._scrape_started = state.started_count
        self._scrape_done = state.completed_count
        self._succ_count = state.success_count
        self._fail_count = state.failure_count

    def request_cancel(self) -> None:
        """Cancel the active session and mirror the request for legacy workers."""
        if self.session is not None:
            self.session.request_cancel()
        self.stop_requested = True


Flags = _Flags()
