# MDCx repository instructions

MDCx 是 PyQt6 本地媒体元数据工具。仓库级原则只有一个：**用最小、可验证的改动解决当前问题，不为未来假设增加架构。**

当前代码、测试和 workflow 是事实来源。版本号、分支、远端、站点协议、CI 状态等易变化信息不要写死在本文件；需要时现场读取。

## 开始任务

1. 先检查 `git status --short --branch`，不要覆盖用户现有改动。
2. 用精准搜索定位目标符号、调用方和相关测试；先读局部，再决定是否扩大范围。
3. 只在任务涉及对应领域时读取 `docs/` 专题文档，不做无目的全仓扫描。
4. `build/`、`dist/`、`.venv/`、缓存、日志、`userdata/` 和生成产物不是源码阅读入口。

## 项目地图

- `main.py`：GUI 入口。
- `mdcx/controllers/`：UI 编排与交互。
- `mdcx/core/`：刮削后的媒体、NFO、图片和文件整理逻辑。
- `mdcx/crawlers/`：站点适配与统一爬虫接口。
- `mdcx/config/`：当前配置、旧配置迁移和持久化。
- `mdcx/models/`：运行状态与领域模型。
- `mdcx/views/`：Designer `.ui` 和生成的 Python 视图。
- `tests/`：离线回归测试；在线站点探测不能替代单元测试。
- `scripts/`：UI 生成、构建、版本、发布和专项诊断脚本。
- `.github/workflows/`：CI / Release 的执行事实来源。

持久架构边界见 `docs/architecture.md`；构建环境疑难问题见 `docs/build-troubleshooting.md`。不要把专题文档复制进 AGENTS.md。

## 修改约束

- 不做与当前任务无关的重构，不顺手全仓格式化。
- 不提交 Cookie、Token、密钥、账号、`MDCx.config` 或其他本地用户数据。
- 修改持久化配置、枚举值、默认值或迁移时，必须兼容已有 INI/JSON；确需改键时提供 migration 和 round-trip 测试。
- 修改真实文件移动/重命名/整理逻辑时保持 fail-closed：不得静默覆盖，需考虑冲突、跨盘、链接、大小写改名和失败回滚。
- 修改 `.ui` 后运行 `uv run --locked python scripts/generate_ui.py` 并提交对应生成文件；不要手改生成视图绕过 Designer 源文件。
- 依赖变更通过 `uv` 更新 `uv.lock`，不要手工编辑锁文件。
- 爬虫解析变化优先增加脱敏本地 fixture；不要把某次在线请求成功当成稳定回归测试。
- 修复应覆盖根因和直接同类路径，但不要因此扩大成无边界“清理工程”。
- 未经任务明确要求，不创建 Tag、Release，不重写 Git 历史。

## 验证策略

验证强度跟随改动风险，而不是每次机械运行全部命令：

- 文档、注释或低风险配置文本：至少 `git diff --check`。
- 普通 Python 改动：Ruff + 最相关 pytest。
- 共享配置、会话状态、网络基础层、文件系统或爬虫公共层：先相关测试，稳定后再扩大范围。
- Designer/UI 改动：生成视图 + 相关控制器/UI 测试；需要时构造 offscreen 主窗口。
- 构建、依赖、发布流程或准备发布：完整离线 pytest、Ruff、必要平台构建/冒烟。

不要为可逆、低影响、只是复述实现细节的改动增加无价值测试。修复回归、边界条件或高风险行为时，应补能真实失败的测试。

常用命令：

```bash
uv sync --locked --all-extras --dev
uv run --locked ruff format --check
uv run --locked ruff check --output-format=concise
uv run --locked pytest <relevant tests> -q
uv run --locked pytest tests -q
git diff --check
uv run --locked python scripts/generate_ui.py
uv run --locked python scripts/build.py --debug
```

`main.py` 顶层会启动事件循环，不作为普通库导入。GUI 冒烟使用 `QT_QPA_PLATFORM=offscreen` 并显式退出。

## Agent / Codex 上下文规则

- 本文件只保存长期、跨任务都成立的约束；不要追加当前 SHA、测试通过数、临时 TODO、某站点当天协议或发布交接日志。
- 优先让代码、类型、测试和小型脚本表达规则；只有反复出现、且无法由现有脚本/文档清楚表达的专用工作流，才值得新增 skill。
- 当前仓库没有必须加载的 `SKILL.md`。不要为了“有一个 skill”而创建常驻上下文；若以后新增，应保持单一用途、按需加载，并避免复制本文件或专题文档。
- 独立只读查询可以并行；有依赖关系的修改与验证按顺序进行。
- 结束时只汇报实际改动、验证结果和仍未验证的风险，不输出冗长过程日志。

## 发布

发布规则以 `.github/workflows/release.yml`、`mdcx/consts.py::LOCAL_VERSION` 和当前 Git Tag/Release 状态为准。需要发布时再读取并核对这些实时来源。
