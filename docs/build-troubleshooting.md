# 构建与排障指南

本文记录 MDCx 4.0 的可复现测试与打包约束。构建发布包时应使用项目锁文件和 `scripts/build.py`，不要直接调用 PyInstaller。

## 标准验收流程

```powershell
uv sync --locked --group dev
uv run --locked ruff format --check
uv run --locked ruff check
uv run --locked pytest tests -q
uv run --locked python scripts/build.py --version 4.0.0
```

`scripts/build.py` 不以“PyInstaller 返回 0”作为最终成功条件。打包后它会启动真实冻结产物并传入 `--smoke-test`，检查 Qt DLL、PyQt6 模块和 MDCx 启动导入树；返回非零、无法启动或 45 秒超时都会使构建失败。这个检查必须保留在本地构建和 Release CI 中。

## Windows EXE“详细信息”必须同步

Windows 文件属性不是手工维护文件。`scripts/build.py` 每次打包都会从 `mdcx/consts.py` 的 `LOCAL_VERSION` 生成 PE 版本资源，写入文件说明、产品名称、文件版本、产品版本、版权、内部名称、原始文件名、项目地址和简体中文语言。

构建结束后脚本会重新读取 `dist/MDCx.exe` 的版本资源，核对应用名、版本、文件说明、版权主体和原始文件名。任何字段缺失或版本未同步都会使构建失败。因此以后升级只修改唯一版本源并使用标准构建脚本，禁止直接运行 PyInstaller 或手工维护另一个版本文件。

## `ImportError: DLL load failed while importing QtCore`

### 已确认的根因

Qt 6.11 的 Windows `Qt6Core.dll` 使用 Windows 自带的 ICU ABI。PyInstaller 会沿构建进程的 `PATH` 搜索 DLL；如果环境里有 Poppler、Anaconda、旧 Qt 或其他软件的 `icuuc.dll`，它可能把同名但 ABI 不兼容的 DLL 收进 EXE。

此时 DLL 文件看似齐全，Windows 仍会报告“找不到指定的程序”。这里的“程序”实际可能是 DLL 导出入口点，而不一定是文件缺失。典型证据是：源码环境可以 `import PyQt6.QtCore`，最小冻结程序却失败；检查冻结归档后发现第三方 `icuuc.dll`/`icudt*.dll`。

### 项目中的永久防护

- Windows spec 在 `Analysis` 后移除 `icuuc.dll` 和 `icudt*.dll`，让 Qt 使用受支持的 Windows System32 ICU。
- 每个构建产物必须通过真实启动 smoke test。
- 不从工作站 PATH 复制 ICU 到 `resources`、`libs` 或发布目录。
- 升级 PyQt6、Qt6、PyInstaller 或 Python 后，必须重新执行完整构建与启动验收。

若问题再次出现，先查看 `build/<应用名>/Analysis-00.toc` 中 `icuuc.dll` 的来源；它不应指向 Poppler、Conda 或其他应用目录。不要通过随意复制 DLL 解决入口点错误，这通常会把 ABI 冲突带进发布包。

## EXE 体积异常增大

`imageio-ffmpeg` 的 wheel 包含完整 FFmpeg 可执行文件。只要生产模块导入它，PyInstaller 的依赖分析就可能把该二进制打进单文件 EXE，造成几十 MB 的额外增长。

MDCx 的约束如下：

- `imageio-ffmpeg` 只属于开发依赖。
- `tests/conftest.py` 将其路径写入 `MDCX_FFMPEG`，确保测试无需系统 FFmpeg。
- 生产代码只读取 `MDCX_FFMPEG` 或系统 `PATH`，不导入 `imageio_ffmpeg`。
- 构建脚本额外排除 `imageio_ffmpeg`，防止未来间接依赖再次收集它。

体积突然增加时，可用 PyInstaller 的归档查看工具检查是否包含 `imageio_ffmpeg/binaries/ffmpeg-*.exe`。正式 MDCx EXE 中不应出现该路径。

## Windows pytest 临时目录

pytest 由 `tests/conftest.py` 为每个进程创建独立的系统临时目录并在退出时清理，项目内只持久化可随时重建的 `.test-cache`。不要固定复用同一个 `--basetemp`，也不要重新指向历史 `.pytest-cache`：测试进程、杀毒软件或异常退出可能让旧目录保留句柄或异常 ACL，导致后续测试在 fixture 初始化阶段报 `PermissionError`。

Qt 测试的 `QT_QPA_PLATFORM=offscreen`、离线模型模式和测试 FFmpeg 路径都由 `tests/conftest.py` 自动配置。日常执行无需管理员权限、Developer Mode、symlink 或系统 FFmpeg。

首次检出或依赖变更后执行 `uv sync --frozen` 创建项目内 `.venv`；后续统一使用该环境运行测试和构建。`uv.toml` 将下载缓存固定到项目内 `.uv-cache`，环境和缓存均可持久复用，避免临时 Python 环境消失后跳过测试。

## 发布前检查表

- 完整测试无跳过、无失败。
- 构建日志包含“冻结程序启动验证通过”。
- EXE 可在未安装 Python 的 Windows 机器启动。
- 归档中没有第三方 `icuuc.dll`、`icudt*.dll` 或测试 FFmpeg。
- 版本号来自 `mdcx/consts.py`，与产物文件名和发布标签一致。
- EXE 属性页包含文件说明、产品名、文件/产品版本、版权和语言，且构建日志包含“Windows 文件属性与应用版本同步验证通过”。
- 工作流不得引用声明 `node20` 的 JavaScript action；升级 action 后先确认其 `runs.using` 为 `node24`。
- 发布资产使用 GitHub CLI 上传；不要重新引入尚未迁移到 Node 24 的旧上传 action。
