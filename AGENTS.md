# MDCx 开发上下文

> 本文件供后续开发会话使用。代码、配置和本文冲突时，以当前磁盘代码为准；开始工作时必须重新检查 Git 状态和相关实现。

## 信息来源和边界

- 仓库通常使用 `origin` 指向 `Kesuy/mdcx`、`upstream` 指向 `Hazard804/mdcx`；操作前仍须用 `git remote -v` 核对。
- 分支、HEAD、工作树、Tag、Release、Actions 和依赖版本都是实时状态，不在本文固化；开始任务时重新查询。
- 应用发布版本以 `mdcx/consts.py::LOCAL_VERSION` 为源，发布记录和版本说明以 Git Tag、GitHub Release 与 `changelog.md` 为准。
- `pyproject.toml` 的 `project.version` 是 Python 包元数据，不应据此猜测 Release Tag。

## 项目用途和主要功能

MDCx 是 GPLv3 授权的 PyQt6 桌面媒体元数据刮削、整理和 NFO 管理工具，面向本地影片库。主要能力包括：

- 按番号识别媒体并从多个网站组合抓取标题、演员、封面、标签、日期等元数据。
- 下载和处理海报、背景图、预告片、演员图片等资源。
- 生成、读取和编辑 NFO，支持本地已有 NFO 工作流。
- 按 Jinja2 命名模板整理目录、视频、字幕和关联素材。
- 支持多 CD 影片、软链接、成功/失败目录、翻译、网络代理和 Cloudflare/FlareSolverr 处理。
- 提供图形界面、部分命令行入口以及 Windows/macOS 打包流程。

项目仅供学习和技术交流；遵守 `README.md` 中的许可和使用限制。

## 技术栈和运行环境

- Python 版本要求以 `pyproject.toml::requires-python` 为准；目标 runner 版本以当前 workflow 为准。
- GUI：PyQt6。
- 依赖管理：uv；锁文件为 `uv.lock`，跨 Linux x86_64、macOS x86_64/arm64、Windows AMD64。
- 网络：`curl-cffi`、`httpx`、`aiofiles`、`aiolimiter`。
- 解析：BeautifulSoup、lxml、parsel。
- 数据模型/配置：Pydantic Settings、JSON；仍支持旧 INI 配置迁移。
- 图像/视频：Pillow、OpenCV headless、PyAV。
- 测试：pytest、pytest-asyncio、pytest-cov。
- 格式和静态检查：Ruff；版本约束见 `pyproject.toml`，CI 使用版本见当前 workflow。
- 打包：PyInstaller；macOS 可额外使用 `create-dmg`。

不要假定系统 Python 可用；优先通过 `uv run` 使用项目环境。

## 主要目录及职责

- `main.py`：PyQt6 桌面程序入口，设置 DPI 策略、主题并创建 `MyMAinWindow`。
- `mdcx/config/`：Pydantic 配置模型、默认值、派生配置、V1 转换和版本迁移。
- `mdcx/controllers/`：主窗口、裁图窗口和 UI 事件/业务编排。
- `mdcx/core/`：媒体扫描、NFO、命名、文件整理和核心业务逻辑。
- `mdcx/crawlers/`：站点刮削器、注册表、解析器和统一结果类型。
- `mdcx/models/`：运行期数据对象和共享类型。
- `mdcx/views/`：Qt Designer `.ui` 文件及生成的 Python UI 文件。
- `mdcx/base/`：较底层的共享 Web/任务基础设施。
- `mdcx/utils/`、`mdcx/tools/`：通用工具及外部服务辅助代码。
- `resources/`：图标、图片、配置模板和映射资源。
- `libs/`：打包时一并携带的项目运行资源。
- `tests/`：按 `controllers/`、`core/`、`crawlers/` 和顶层集成测试组织。
- `scripts/`：构建、版本更新、changelog、Qt UI 生成及维护脚本。
- `.github/workflows/`：质量检查和跨平台 Release 构建。
- `build/`、`dist/`、`.venv/`、缓存、日志、`userdata/`：本地产物或用户数据，不作为源码阅读入口。

## 程序和命令入口

- GUI：`uv run --locked python main.py`
- 单次刮削 CLI：`uv run crawl --help`
- 生成枚举：`uv run --locked gen_enums`（会覆写 `mdcx/gen/field_enums.py`）
- 构建：`uv run build --help` 或 `uv run scripts/build.py --help`
- 更新版本：`uv run bump --help`
- 生成 changelog：`uv run changelog --help`
- 重新生成 Qt UI：`uv run --locked bash scripts/pyuic.sh`

`main.py` 在模块顶层启动 event loop，不适合作为普通库导入。GUI 冒烟测试应使用 `QT_QPA_PLATFORM=offscreen` 并显式控制退出。

## 安装、启动、测试和构建

```bash
# 安装并严格使用锁文件，包括开发依赖
uv sync --locked --all-extras --dev

# 启动桌面程序
uv run --locked python main.py

# 运行完整离线测试
uv run --locked pytest tests/ -q

# 运行相关测试示例
uv run --locked pytest tests/crawlers/test_fc2ppvdb.py -q
uv run --locked pytest tests/controllers/test_responsive_layout.py -q

# 网络爬虫测试默认关闭；仅在明确需要且凭据安全时启用
uv run --locked pytest tests/crawlers --network --site fc2ppvdb

# 格式、静态检查和语法检查
uv run --locked ruff format --check
uv run --locked ruff check --output-format=concise
uv run --locked python -m compileall -q mdcx main.py scripts
git diff --check

# 本地 PyInstaller 构建；--debug 保留 build/ 和 .spec 便于诊断
uv run --locked scripts/build.py --debug
```

爬虫测试的 `--network`、`--site`、`--overwrite` 和 `--parser-name` 参数定义于 `tests/crawlers/conftest.py`；参数行为变化时以该文件为准。

## Git 分支和提交规范

- 修改前先运行 `git status --short --branch`，确认分支、未提交文件和是否存在他人改动。
- 不假定当前分支就是发布分支；提交或发布前核对 branch、remote、保护规则和目标 commit，避免推到错误 remote。
- 近期提交使用 Conventional Commits 风格：`feat:`、`fix:`、`docs:`、`chore:`；保持提交单一、可审查。
- 不覆盖、丢弃或混入现有未提交改动，不执行无授权的 hard reset、rebase 或历史重写。
- 未经明确授权，不提交、推送、创建 Tag 或发布 Release。
- 提交前检查 staged 与 unstaged 内容，确保测试验证的是将要提交的同一份代码。

## 修改代码时必须遵守的规则

1. 修改前先查看 `git status`。
2. 优先精准搜索和读取相关文件、符号及调用链，不扫描整个仓库。
3. 不全量读取或提交 `build/`、`dist/`、`.venv/`、缓存、依赖、日志、`userdata/` 等大型或本地目录。
4. 不进行与当前任务无关的重构，不修改无关文件，不顺手全仓格式化。
5. 不提交缓存、日志、Cookie、Token、密钥、账号密码、`MDCx.config` 或本地配置。
6. 修改后运行最相关测试；影响共享配置、网络、文件系统或发布流程时扩大到完整测试。
7. 修复根因并覆盖同类路径；网站解析变化应使用脱敏本地 fixture，不能把真实 Cookie 写入测试。
8. 代码和聊天描述冲突时，以当前代码为准；必要时查看 `git log -p` 理解兼容逻辑的意图。
9. 修改 `.ui` 时同步生成对应 `.py`，并检查差异只包含预期 UI 变化。
10. 文件移动/NFO 整理属于高风险操作：先补失败、冲突和回滚测试，再改实现。
11. 不把在线网站偶发成功当作单元测试；在线探测与离线行为测试必须分开记录。
12. 未经明确授权，不提交、推送、创建 Tag 或发布 Release。

## 不允许随意修改的兼容逻辑

- `mdcx/consts.py` 中 `MAIN_PATH`、`MARK_FILE` 和不同平台/PyInstaller 下的数据目录语义。
- `mdcx/config/manager.py` 的 `MDCx.config` 指针文件、JSON 配置加载和旧 `.ini` 到 `.v2.json` 转换。
- `mdcx/config/v1.py` 与 `mdcx/config/migrations.py` 中旧字段、网站列表、代理和命名模板迁移；修改必须有转换测试。
- `mdcx/config/enums.py::Website` 的持久化值和 `mdcx/crawlers/__init__.py` 注册关系。枚举值可能已写入用户配置。
- FC2CMADB 当前仍沿用内部标识/配置字段 `fc2ppvdb`；不要只因站点改名就重命名持久化键。
- FC2CMADB 从 `/articles/<number>` 的 Inertia `props.article` 读取详情；若 `deferredProps` 声明 `actresses`，需用 partial headers 请求同一 URL，并在有页面版本时传递 `X-Inertia-Version`。无 deferred prop 时保留内联 `article.actresses` 兼容。
- FC2CMADB 登录使用完整 Cookie 请求头，当前有效会话键为 `fc2cmadb-session`；不得恢复旧 `fc2ppvdb_session` 兼容，也不得把真实 Cookie 放入源码、fixture 或日志。
- FC2CMADB/Cloudflare Cookie 可能绑定浏览器 TLS fingerprint 与 User-Agent；认证详情页及 Inertia deferred 请求必须保持同一浏览器画像。当前通过 `fingerprint_id="chrome136_win"` 固定画像，不能恢复为随机画像。
- FC2CMADB 的 `article.censored` 可能为空；类型判断须保留基于“無修正”标签的回退。
- `mdcx/crawlers/base/` 的统一 `CrawlerResponse`/`CrawlerResult` 行为及新旧爬虫迁移边界，参见 `docs/crawler-migration.md`。
- `mdcx/core/media_reorganization.py` 的目标冲突、同文件系统、symlink/junction、防覆盖、大小写改名和回滚保护。
- 多 CD 分组及关联字幕/NFO/图片路径同步；不能以“简化”为由跳过安全预检查。
- `mdcx/views/MDCx.ui` 与生成文件 `mdcx/views/MDCx.py` 必须保持同步。
- `uv.lock` 必须随依赖变更更新；不要手工编辑锁文件。

## 已知风险和常见问题

- 外部网站会改变 HTML、SPA 数据、登录和 Cloudflare 规则；爬虫问题先检查状态码、最终 URL 和当前响应结构。
- GUI 有大量固定几何布局；不要用透明拖动条只调整少量坐标来模拟可调三栏。若需可调栏宽，应迁移完整 pane 到 Qt layout/`QSplitter`，并验证所有子控件和 DPI 缩放。
- NFO 保存后的自动整理会移动真实文件；跨盘、路径链接、目标冲突或混合影片目录必须 fail closed。
- PyInstaller 构建成功不代表目标平台可用；GUI、文件移动、配置路径和 DPI 行为必须在目标系统验证。

## Windows 打包注意事项

- Windows 构建使用 `uv sync --locked --all-extras --dev` 后运行 `uv run scripts/build.py --debug`，预期产物为 `dist/MDCx.exe`。
- `scripts/build.py` 生成 windowed、one-file PyInstaller 应用，并打包 `resources/`、`libs/`、图标和 `curl_cffi` 数据；修改资源路径或 hidden imports 后必须重新构建。
- 打包态 Windows 的 `MAIN_PATH` 是当前工作目录；双击 EXE 时通常是 EXE 所在目录。`MDCx.config` 指针文件和用户数据路径依赖该语义，不可随意改成源码目录或临时解包目录。
- Windows CI 使用 UTF-8 输出环境；构建/发布脚本输出中文时保持显式 UTF-8，避免 runner 编码错误。
- 发布前至少验证 EXE 启动、窗口调整与 DPI 缩放、最小尺寸、配置读写，以及 NFO/媒体整理的路径和回滚行为。Linux offscreen 冒烟测试不能替代 Windows 验证。

## 版本和发布约束

- `LOCAL_VERSION` 是整数，`scripts/build.py` 将其十进制文本用作应用版本；使用 `uv run bump --help` 更新，不手工维护本文中的版本号。
- `scripts/changelog.py` 和 `.github/workflows/release.yml` 当前以 `220*` 匹配发布 Tag。这只是仓库工具约定，不足以单独证明某个具体 Tag 正确；应结合 `LOCAL_VERSION`、`changelog.md`、目标 commit 和远端未占用状态核对。
- `changelog.md` 只记录待发布版本的改动，不累积复制历史版本内容；Release workflow 根据当前 Tag 与最近祖先 Tag 的提交范围生成本次说明，避免重复旧更新日志。
- 版本变更记录只维护在每次发布对应的 `changelog.md`、Git Tag 和 GitHub Release，不在本文复制完整历史。
- 已存在的发布 Tag 不得移动、覆盖或复用于新代码。发现目标 commit 有缺陷时，先修复、重新验证并更新版本/目标 commit，不得为了沿用旧 SHA 发布已知缺陷。
- GitHub Release 对象存在不代表构建完成；必须等待 workflow 成功并确认预期附件已上传。

### 发布前和发布后检查

1. `git fetch origin --tags`，检查 `git status --short --branch`、remote、目标分支和目标 commit。
2. 从源码读取 Tag，并检查同名本地/远端 Tag 和 Release；任何已存在或指向不一致的结果都应停止自动发布。
3. 审查 staged/unstaged diff，扫描敏感信息；运行相关测试、完整离线测试、Ruff、`compileall`、锁文件同步、构建和基本启动检查。
4. 对 UI、文件系统和打包变更执行对应 Windows/macOS 验证；检查 `changelog.md`、Release notes 与提交内容一致。
5. 用 `gh auth status` 和 `gh repo view Kesuy/mdcx` 核对身份与权限。只有用户明确授权后才提交、推送、创建 Tag 或发布。

```bash
TAG=$(uv run --locked python -c 'from mdcx.consts import LOCAL_VERSION; print(LOCAL_VERSION)')
COMMIT=$(git rev-parse HEAD)
git ls-remote --tags origin "refs/tags/$TAG"
gh release view "$TAG" -R Kesuy/mdcx

gh release create "$TAG" -R Kesuy/mdcx \
  --target "$COMMIT" --title "$TAG" \
  --generate-notes --latest --fail-on-no-commits
```

6. 检查 `.github/workflows/release.yml` 是否自动启动；未启动时按其当前 `workflow_dispatch` inputs 手动触发，不猜参数。
7. 用 `gh run watch <RUN_ID> -R Kesuy/mdcx --exit-status` 等待结束；失败时读取 `--log-failed` 并只修复构建/发布原因。
8. 最终核对 Tag 指向、正式/预发布状态、Latest、Windows x86_64 `.exe` 和 workflow 承诺的其他附件。未看到 EXE 前不得宣称发布完成。
