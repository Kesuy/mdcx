# MDCx 开发上下文

> 本文件供后续开发会话使用。代码、配置和本文冲突时，以当前磁盘代码为准；开始工作时必须重新检查 Git 状态和相关实现。

## 信息来源和边界

- 仓库通常使用 `origin` 指向 `Kesuy/mdcx`、`upstream` 指向 `Hazard804/mdcx`；操作前仍须用 `git remote -v` 核对。
- 分支、HEAD、工作树、Tag、Release、Actions 和依赖版本都是实时状态，不在本文固化；开始任务时重新查询。
- 应用发布版本以 `mdcx/consts.py::LOCAL_VERSION` 为源；当前发布线使用 `3.0` 起的语义版本字符串，发布记录和版本说明以 Git Tag、GitHub Release 与 `changelog.md` 为准。
- `pyproject.toml` 的 `project.version` 是 Python 包元数据，不应据此猜测 Release Tag。

## 断续开发与上下文节省

- `AGENTS.md` 只保存长期约束，不记录本轮进度、测试通过数、当前 SHA 或待办；临时状态从 `git status`、`git diff` 和会话记录恢复。
- 新会话先用一次批量检查获取 `git status --short --branch`、相关文件 diff 和精准符号搜索；不要重新全仓扫描，也不要重复读取已自动注入的本文件。
- 只加载与当前任务直接相关的 skill/reference，只读取目标函数及调用方；独立的只读查询应并行，避免每个文件单独一轮工具调用。
- 验证按“单个失败测试 → 相关测试 → 完整离线测试/质量门”递进；完整套件通常在功能稳定或交接前运行一次，不在每个小修改后重复。
- 优先使用本地 `uv`、pytest、Ruff 和小型脚本验证；只有独立且推理密集的工作才启动 subagent，避免为机械检查消耗额外模型配额。
- 暂停前确保磁盘代码可恢复、`.ui` 已生成对应 `.py`、新增行为有测试，并在回复中写清“已验证/未验证”；不要把交接日志追加到本文件。

## 项目用途

MDCx 是 GPLv3 的 PyQt6 本地媒体元数据工具，负责番号识别、多站点刮削、图片/NFO 处理、Jinja2 命名整理、多 CD 与关联素材同步，并提供桌面 UI、少量 CLI 和 Windows/macOS 打包。遵守 `README.md` 的许可和使用限制。

## 技术栈和运行环境

Python/依赖版本以 `pyproject.toml`、`uv.lock` 和 workflow 为准。核心栈为 PyQt6、Pydantic、curl-cffi/httpx、BeautifulSoup/lxml/parsel、Pillow/OpenCV/PyAV、pytest、Ruff 和 PyInstaller。仍需兼容旧 INI 迁移。不要假定系统 Python 可用，优先 `uv run --locked`。

## 主要目录

- `main.py` 为 GUI 入口；`mdcx/config/` 管配置与迁移；`controllers/` 管 UI 编排；`core/` 管媒体/NFO/整理；`crawlers/` 管站点；`views/` 保存 `.ui` 与生成代码。
- `base/`、`models/`、`utils/`、`tools/` 为共享基础；`resources/`、`libs/` 为打包资源；`tests/`、`scripts/`、`.github/workflows/` 分别放测试、维护脚本和 CI。
- `build/`、`dist/`、`.venv/`、缓存、日志、`userdata/` 是本地产物，不作为源码阅读入口。

## 常用命令

```bash
uv sync --locked --all-extras --dev
uv run --locked python main.py
uv run --locked pytest tests/ -q
uv run --locked ruff format --check
uv run --locked ruff check --output-format=concise
uv run --locked python -m compileall -q mdcx main.py scripts
git diff --check
uv run --locked bash scripts/pyuic.sh
uv run --locked scripts/build.py --debug
```

`main.py` 顶层启动 event loop，不应作为普通库导入；GUI 冒烟使用 `QT_QPA_PLATFORM=offscreen` 并显式退出。网络爬虫测试默认关闭，参数以 `tests/crawlers/conftest.py` 为准。`gen_enums` 会覆写 `mdcx/gen/field_enums.py`，只在确需生成时运行。

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
12. 不覆盖现有改动或重写历史；未经明确授权不提交、推送、Tag 或发布。提交采用单一、可审查的 Conventional Commit，并核对 staged/unstaged、branch、remote 与目标 commit。
13. **所有功能、修复和重构都必须保持现有 INI 配置兼容**；即使任务没有提到配置，也要检查是否改变旧键、默认值、枚举持久化值、迁移顺序或配置文件定位。

## 配置兼容性是每次改动的硬性门槛

- 旧 `.ini`、`MDCx.config` 指针和当前 JSON 配置都属于用户持久数据；不得要求用户删除配置、重建配置或手工补键才能升级。
- 新配置项必须在当前 `Config`、旧 `ConfigV1`/转换路径、默认配置、设置页加载和保存中形成完整闭环。旧 INI 缺少新键时使用兼容默认值；旧 INI 明确写入的值必须原样迁移并可再次保存。
- 不重命名或复用已持久化的键、`Website` 枚举值、下载字段值和内部站点标识。确需变更时，先写版本化 migration，并保留旧输入解析。
- 修改配置模型、默认值、枚举、设置 UI、load/save binding 或路径逻辑时，必须增加转换与 round-trip 测试，至少覆盖“旧配置缺键”和“旧配置显式值”两种情况。
- 与配置无关的 UI 临时状态（例如裁切比例、旋转次数）不要写入 INI/JSON，避免无必要地扩大配置格式；关闭窗口后恢复默认即可。
- 发布前使用真实旧版脱敏 INI fixture 做一次迁移验证，并确认用户原文件不被破坏。任何无法解析的字段必须 fail safely 并给出日志，不能静默重置整份配置。

## 不允许随意修改的兼容逻辑

- `mdcx/consts.py` 中 `MAIN_PATH`、`MARK_FILE` 和不同平台/PyInstaller 下的数据目录语义。
- `mdcx/config/manager.py` 的 `MDCx.config` 指针文件、JSON 配置加载和旧 `.ini` 到 `.v2.json` 转换。
- `mdcx/config/v1.py` 与 `mdcx/config/migrations.py` 中旧字段、网站列表、代理和命名模板迁移；修改必须有转换测试。
- `mdcx/config/enums.py::Website` 的持久化值和 `mdcx/crawlers/__init__.py` 注册关系。枚举值可能已写入用户配置。
- FC2CMADB 继续使用持久化标识 `fc2ppvdb`；当前 Cookie 键为 `fc2cmadb-session`，不得恢复 `fc2ppvdb_session` 或记录真实 Cookie。
- 详情从 `/articles/<number>` 的 Inertia `props.article` 读取；声明 deferred `actresses` 时以相同 URL、partial headers、可用的 `X-Inertia-Version` 和同一 `chrome136_win` 浏览器画像请求，未声明时兼容内联 actresses。
- `article.censored` 为空时保留“無修正”标签回退。修改 FC2CMADB 前先读当前 crawler、测试和调用链，不凭旧站点经验猜协议。
- `mdcx/crawlers/base/` 的统一 `CrawlerResponse`/`CrawlerResult` 行为及新旧爬虫迁移边界，参见 `docs/crawler-migration.md`。
- `mdcx/core/media_reorganization.py` 的目标冲突、同文件系统、symlink/junction、防覆盖、大小写改名和回滚保护。
- 多 CD 分组及关联字幕/NFO/图片路径同步；不能以“简化”为由跳过安全预检查。
- `mdcx/views/MDCx.ui` 与生成文件 `mdcx/views/MDCx.py` 必须保持同步。
- `uv.lock` 必须随依赖变更更新；不要手工编辑锁文件。

## 已知风险和常见问题

- 外部网站会改变 HTML、SPA 数据、登录和 Cloudflare 规则；爬虫问题先检查状态码、最终 URL 和当前响应结构。
- GUI 有大量固定几何布局；不要用透明拖动条只调整少量坐标来模拟可调三栏。若需可调栏宽，应迁移完整 pane 到 Qt layout/`QSplitter`，并验证所有子控件和 DPI 缩放。
- 封面裁切窗口的显示坐标必须按当前缩放图换算到实际参与裁切的图像；旋转后宽高、裁切框边界、比例锁定、poster/thumb/fanart 输出必须一致。同路径源图用排他唯一临时文件、保留权限并原子替换，失败时不得破坏源图。修改 `.ui` 后运行 `scripts/pyuic.sh`，不要手改生成文件。
- 本地同番号图片按规范化番号匹配并在成功整理阶段移动；文件名排序第一张才是艺术图来源。PNG/WebP 生成 `.jpg` 时必须真实转码，水印和裁切继续走既有策略，失败路径不得提前移动或丢失原文件。
- NFO 保存后的自动整理会移动真实文件；跨盘、路径链接、目标冲突或混合影片目录必须 fail closed。
- PyInstaller 构建成功不代表目标平台可用；GUI、文件移动、配置路径和 DPI 行为必须在目标系统验证。

## Windows 打包注意事项

- Windows 构建使用 `uv sync --locked --all-extras --dev` 后运行 `uv run scripts/build.py --debug`，预期产物为 `dist/MDCx.exe`。
- `scripts/build.py` 生成 windowed、one-file PyInstaller 应用，并打包 `resources/`、`libs/`、图标和 `curl_cffi` 数据；修改资源路径或 hidden imports 后必须重新构建。
- 打包态 Windows 的 `MAIN_PATH` 是当前工作目录；双击 EXE 时通常是 EXE 所在目录。`MDCx.config` 指针文件和用户数据路径依赖该语义，不可随意改成源码目录或临时解包目录。
- Windows CI 使用 UTF-8 输出环境；构建/发布脚本输出中文时保持显式 UTF-8，避免 runner 编码错误。
- 发布前至少验证 EXE 启动、窗口调整与 DPI 缩放、最小尺寸、配置读写，以及 NFO/媒体整理的路径和回滚行为。Linux offscreen 冒烟测试不能替代 Windows 验证。

## 版本和发布约束

- `LOCAL_VERSION` 是从 `3.0` 起的语义版本字符串；build、更新检查、bump、changelog、workflow 必须共同接受点分版本，不能用浮点、整数或普通字符串比较。
- `3.x` 高于旧 `220...` 版本线；GitHub Latest Tag 经统一解析后比较，异常 Tag 只记日志，不得让主界面崩溃。读取 `LOCAL_VERSION` 必须完整解析赋值，不能把 `3.1-alpha` 截断成 `3.1`；包括 dry-run 在内的入口都须在提前返回前校验。
- Release Tag 必须与 `LOCAL_VERSION` 文本完全一致，使用不带 `v` 前缀的点分数字；artifact 名使用已验证的 Tag commit，不能依赖事件语义不同的 `github.sha`。Tag glob 不能单独证明 Tag 正确，仍须核对版本、changelog、目标 commit 和远端占用状态。
- `changelog.md` 只记录待发布版本的改动，不累积复制历史版本内容；Release workflow 根据当前 Tag 与最近祖先 Tag 的提交范围生成本次说明，避免重复旧更新日志。
- 版本变更记录只维护在每次发布对应的 `changelog.md`、Git Tag 和 GitHub Release，不在本文复制完整历史。
- 已存在的发布 Tag 不得移动、覆盖或复用于新代码。发现目标 commit 有缺陷时，先修复、重新验证并更新版本/目标 commit，不得为了沿用旧 SHA 发布已知缺陷。
- GitHub Release 对象存在不代表构建完成；必须等待 workflow 成功并确认预期附件已上传。

### 发布前和发布后检查

1. `git fetch origin --tags` 后核对 status、remote、目标分支/commit；从 `LOCAL_VERSION` 读取 Tag，检查同名本地/远端 Tag 和 Release，已占用或指向不一致则停止。
2. 审查 staged/unstaged diff与敏感信息；运行相关及完整离线测试、Ruff、`compileall`、锁文件同步、构建和启动冒烟；UI/文件系统改动还需目标平台验证。
3. 用 `gh auth status`、`gh repo view Kesuy/mdcx` 核对身份权限。只有用户明确授权后才提交、推送、Tag 或发布；Release 必须显式绑定已验证 commit，使用 `--fail-on-no-commits`。
4. 检查 `release.yml` 是否启动；必要时按现有 `workflow_dispatch` inputs 触发。用 `gh run watch <RUN_ID> -R Kesuy/mdcx --exit-status` 等待，失败时读 `--log-failed`。
5. 最终核对 Tag 指向、Latest、发布类型和附件；未看到 Windows x86_64 `.exe`（以及 workflow 承诺的其他附件）前不得宣称完成。
