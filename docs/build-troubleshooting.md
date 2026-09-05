# 构建与排障指南

本文只记录难以从代码表面重新推导、且长期可能复现的构建问题。常规测试、版本校验和发布步骤以 `AGENTS.md`、`scripts/build.py` 与 `.github/workflows/` 为准，不在这里复制一套易过期流程。

## 标准构建入口

首次检出或依赖变化后使用锁文件同步环境：

```bash
uv sync --locked --all-extras --dev
```

构建统一走：

```bash
uv run --locked python scripts/build.py
```

不要直接调用 PyInstaller。`scripts/build.py` 会从 `mdcx/consts.py` 读取版本、生成平台构建配置，并对冻结产物执行真实启动 smoke test；构建返回 0 本身不代表最终可发布。

## Windows：`ImportError: DLL load failed while importing QtCore`

### 常见根因

Windows 构建环境中的 Poppler、Conda、旧 Qt 或其他软件可能把同名但 ABI 不兼容的 ICU DLL 暴露到 `PATH`。PyInstaller 依赖分析若把这些 DLL 收进冻结产物，源码环境仍可能正常 `import PyQt6.QtCore`，而 EXE 启动时报 DLL load failed。

### 诊断

先查看构建目录中的 PyInstaller Analysis 记录，确认 `icuuc.dll` / `icudt*.dll` 的来源。它们不应来自 Poppler、Conda 或其他应用目录。

### 项目防护

- 构建脚本在 Windows spec 中排除冲突 ICU DLL，让 Qt 使用受支持的系统 ICU。
- 每个构建产物都必须通过真实冻结启动 smoke test。
- 不要通过手工复制 ICU DLL 到 `resources`、`libs` 或发布目录解决入口点错误。
- 升级 Python、PyQt6/Qt6 或 PyInstaller 后，应重新执行完整平台构建验证。

## EXE 体积突然增大

`imageio-ffmpeg` wheel 自带完整 FFmpeg 可执行文件。生产模块一旦直接或间接导入它，PyInstaller 可能把该二进制一起打入 EXE。

MDCx 的约束：

- `imageio-ffmpeg` 只作为测试/开发依赖提供已知可用的 FFmpeg。
- `tests/conftest.py` 把测试 FFmpeg 路径写入 `MDCX_FFMPEG`。
- 生产代码只读取 `MDCX_FFMPEG` 或系统 `PATH`，不导入 `imageio_ffmpeg`。
- 构建脚本显式排除 `imageio_ffmpeg`。

若体积异常，检查 PyInstaller 归档中是否出现 `imageio_ffmpeg/binaries/ffmpeg-*`；正式产物不应包含该路径。

## Windows pytest 临时目录 `PermissionError`

Windows 上异常退出、杀毒软件或残留句柄可能让旧 pytest 临时目录保留异常 ACL。固定复用 `--basetemp` 会让后续测试在 fixture 初始化阶段继续失败。

项目由 `tests/conftest.py` 为测试进程创建新的系统临时根目录，并在退出时尽力清理。不要重新固定历史 `.pytest-cache` / `.test-cache` 作为 basetemp。pytest 的可重建缓存仅由 `pyproject.toml` 的 `cache_dir` 管理。

Qt 测试的 offscreen 模式、离线模式和测试 FFmpeg 也由 `tests/conftest.py` 统一配置，日常测试不应依赖管理员权限、Developer Mode 或系统 FFmpeg。

## 冻结产物 smoke test 失败

源码可启动不代表冻结产物可启动。遇到构建后 smoke test 失败时，优先检查：

1. PyInstaller 是否误收集了工作站环境中的同名 DLL 或大型开发依赖；
2. Qt/PyQt6 模块和资源是否进入冻结导入树；
3. `resources/` 与平台图标等必需文件是否存在；
4. 最近的 Python、Qt、PyInstaller 或依赖升级是否改变了冻结行为。

不要跳过 smoke test 来“让发布通过”。如果本地问题只在某个平台复现，应在对应平台构建中修复根因，再由 CI / Release workflow 做最终发布验证。
