import json
import os
import os.path
import sys
import threading
from pathlib import Path
from types import TracebackType

from ..consts import IS_PYINSTALLER, MAIN_PATH, MARK_FILE
from ..utils import executor
from .computed import Computed
from .models import Config
from .v1 import ConfigV1, load_v1


class ConfigManager:
    def __init__(self):
        self._computed_lock = threading.RLock()
        marked_path = self._read_marked_path()
        if marked_path is not None and marked_path.is_file():
            self._set_path(marked_path)
        else:
            # 指针丢失或已失效时，优先恢复当前程序目录中最近修改的 JSON 配置。
            # 这也能处理用户移动整个便携目录后 MDCx.config 仍指向旧绝对路径的情况。
            fallback = self._latest_json_config(MAIN_PATH) or MAIN_PATH / "config.json"
            self.path = fallback
        if not os.path.exists(self._path):  # 配置文件不存在, 写入默认值
            if self._path.suffix == ".ini":
                self.path = self._path.with_suffix(".json")
            self.reset()
        self.load()

    @staticmethod
    def _latest_json_config(folder: Path) -> Path | None:
        """返回目录中最后修改的 JSON 文件，目录不可读时安全回退。"""
        try:
            candidates = [path for path in folder.iterdir() if path.is_file() and path.suffix.lower() == ".json"]
        except OSError:
            return None

        def sort_key(path: Path) -> tuple[int, str]:
            try:
                modified = path.stat().st_mtime_ns
            except OSError:
                modified = -1
            return modified, path.name.casefold()

        return max(candidates, key=sort_key, default=None)

    @staticmethod
    def _read_marked_path() -> Path | None:
        if not MARK_FILE.is_file():
            return None
        try:
            value = ConfigManager.read_mark_file()
        except OSError:
            return None
        if not value:
            return None
        path = Path(value).expanduser()
        return path if path.is_absolute() else MAIN_PATH / path

    def _set_path(self, path: str | Path) -> None:
        self._path = Path(path)
        self.data_folder, self.file = self._path.parent, self._path.name

    @property
    def path(self) -> Path:
        return self._path

    @path.setter
    def path(self, path: str | Path):
        p = Path(path)
        self._set_path(p)
        self.write_mark_file(p)  # 更新标记文件路径

    def load(self) -> list[str]:
        if self._path.suffix == ".ini":  # handle v1 config
            return self.handle_v1()
        try:
            d = json.loads(self._path.read_text(encoding="UTF-8"))
            errors = Config.update(d)
            config = Config.model_validate(d)
            self._replace_config(config)
            return errors
        except Exception as e:
            self._replace_config(Config())
            msg = f" 配置文件 {self._path} 验证失败. 错误信息: \n{str(e)}"
            return msg.splitlines()

    def handle_v1(self):
        v2path = self.path.with_suffix(".v2.json")
        v1path = self.path
        if os.path.exists(v2path):
            self.path = v2path
            return [f"[V1] {v1path} 是旧版配置文件, 对应的新版配置文件已存在, 改为加载新版配置: {v2path}"] + self.load()

        d, errors = load_v1(self.path)
        self.path = v2path
        errors = [
            f"[V1] {v1path} 是旧版配置文件, 将自动转换为新版配置并保存到 {v2path}",
            "[V1] 旧版配置文件不会被删除. 当保存配置时, 仅会写入新版配置文件, 后续会自动使用新版配置文件",
        ] + errors
        config_v1 = ConfigV1(**d)
        config_v1.init()
        self._replace_config(config_v1.to_pydantic_model())
        self.save()
        return errors

    def _replace_config(self, config: Config) -> None:
        """热切换配置派生对象，旧对象等待持有方释放后再关闭。"""
        computed = Computed(config)
        with self._computed_lock:
            old_computed = getattr(self, "computed", None)
            self.config = config
            self.computed = computed
        self._close_old_computed(old_computed)

    def acquire_computed(self) -> "ComputedLease":
        return ComputedLease(self)

    def _close_old_computed(self, old_computed: Computed | None):
        if old_computed is None:
            return
        executor.submit(old_computed.close_when_idle())

    def save(self):
        self._path.write_text(self.config.model_dump_json(indent=2), encoding="UTF-8")

    def reset(self):
        """写入默认配置"""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        template_path = self._get_default_template_path()
        if template_path.is_file():
            try:
                template = json.loads(template_path.read_text(encoding="UTF-8"))
                Config.update(template)
                self._path.write_text(Config.model_validate(template).model_dump_json(indent=2), encoding="UTF-8")
                return
            except Exception:
                pass
        self._path.write_text(Config().model_dump_json(indent=2), encoding="UTF-8")

    @staticmethod
    def _get_default_template_path() -> Path:
        if IS_PYINSTALLER:
            try:
                return Path(sys._MEIPASS) / "resources" / "config" / "default_config.json"  # type: ignore[attr-defined]
            except Exception:
                pass
        return MAIN_PATH / "resources" / "config" / "default_config.json"

    def list_configs(self) -> list[str]:
        """列出配置文件夹中的所有配置文件名."""
        if not self._path.parent.exists():
            return []
        return [f.name for f in self._path.parent.iterdir() if f.suffix in (".json", ".ini")]

    @staticmethod
    def write_mark_file(path: str | Path):
        """写入 MARK_FILE"""
        if not os.path.exists(MARK_FILE):  # 标记文件不存在
            # 确保 MARK_FILE 所在目录存在
            mark_dir = os.path.dirname(MARK_FILE)
            if mark_dir:
                os.makedirs(mark_dir, exist_ok=True)
        with open(MARK_FILE, "w", encoding="UTF-8") as f:
            f.write(str(path))

    @staticmethod
    def read_mark_file() -> str:
        """读取 MARK_FILE"""
        with open(MARK_FILE, encoding="UTF-8") as f:
            return f.read().strip()


class ComputedLease:
    def __init__(self, manager: ConfigManager):
        self._manager = manager
        self._computed: Computed | None = None
        self._entered = False

    def _enter(self) -> Computed:
        if self._entered:
            raise RuntimeError("Computed 租约不能重复进入")
        with self._manager._computed_lock:
            computed = self._manager.computed
            computed.retain()
        self._computed = computed
        self._entered = True
        return computed

    def __enter__(self) -> Computed:
        return self._enter()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        computed = self._computed
        if computed is not None:
            self._computed = None
            executor.run(computed.release())

    async def __aenter__(self) -> Computed:
        return self._enter()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        computed = self._computed
        if computed is not None:
            self._computed = None
            await computed.release()


manager = ConfigManager()


def get_new_str(a: str, wanted=False):
    return a
