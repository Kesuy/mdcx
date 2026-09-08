# MDCx repository instructions

MDCx 是 PyQt6 本地媒体元数据工具。仓库级原则只有一个：**用最小、可验证的改动解决当前问题，不为未来假设增加架构。**

用户请求定义任务范围。明确的改动请求直接实施，并在该范围内完成必要的调查、修改和验证；只有缺少会改变结果的关键信息，或动作不可逆、超出范围时才询问。

## 开始任务

1. 先检查 `git status --short --branch`，不要覆盖用户现有改动。
2. 用精准搜索定位目标符号、调用方和相关测试；先读局部，证据不足时再扩大范围。
3. 当前代码、测试和 workflow 是事实来源。版本号、分支、远端、站点协议和 CI 状态等易变信息现场读取。
4. 只按任务需要读取 `docs/`；`build/`、`dist/`、`.venv/`、缓存、日志、`userdata/` 和生成产物不是源码入口。

## 项目地图

- `main.py` 是 GUI 入口；`mdcx/controllers/` 和 `mdcx/views/` 负责 UI 编排、Designer `.ui` 及生成视图。
- `mdcx/core/` 负责媒体、NFO、图片和文件整理；`mdcx/crawlers/` 负责站点适配与统一接口。
- `mdcx/config/` 和 `mdcx/models/` 负责配置迁移、持久化、运行状态与领域模型。
- `tests/` 是离线回归测试；`scripts/` 与 `.github/workflows/` 是生成、构建、诊断和发布流程的事实来源。在线探测不能替代单元测试。

持久架构边界见 `docs/architecture.md`；构建环境疑难问题见 `docs/build-troubleshooting.md`。不要把专题文档复制进 AGENTS.md。

## 修改约束

- 不做与当前任务无关的重构，不顺手全仓格式化。
- 不提交 Cookie、Token、密钥、账号、`MDCx.config` 或其他本地用户数据。
- 修改持久化配置、枚举值、默认值或迁移时，必须兼容已有 INI/JSON；确需改键时提供 migration 和 round-trip 测试。
- 修改真实文件移动/重命名/整理逻辑时保持 fail-closed：不得静默覆盖，需考虑冲突、跨盘、链接、大小写改名和失败回滚。
- 修改 `.ui` 后运行 `uv run --locked python scripts/generate_ui.py` 并提交对应生成文件；不要手改生成视图绕过 Designer 源文件。
- 依赖变更通过 `uv` 更新 `uv.lock`，不要手工编辑锁文件。
- 爬虫解析变化优先增加脱敏本地 fixture；不要把某次在线请求成功当成稳定回归测试。
- 修复覆盖根因和直接同类路径，不扩大成无边界清理。
- 未经任务明确要求，不创建 Tag、Release，不重写 Git 历史。

## 验证策略

验证强度跟随改动风险：

- 文档、注释或低风险配置文本：至少 `git diff --check`。
- 普通 Python 改动：Ruff + 最相关 pytest。
- 共享配置、会话状态、网络基础层、文件系统或爬虫公共层：先相关测试；只有失败或未解风险才扩大范围。
- Designer/UI 改动：生成视图 + 相关控制器/UI 测试；需要时构造 offscreen 主窗口。
- 构建、依赖、发布流程或准备发布：完整离线 pytest、Ruff、必要平台构建/冒烟。

不为可逆、低影响且只是复述实现的改动增加测试。回归、边界条件和高风险行为应补能真实失败的测试。

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

## Codex 上下文

- 用户明确要求优先于 skill 的一般指南；若 skill 导致暂停或偏离，指出具体 `SKILL.md` 与规则。
- 本文件只保存长期、跨任务约束；不追加当前 SHA、测试数量、临时 TODO、站点当天协议或发布交接日志。
- 优先用代码、类型、测试和小脚本表达规则。仅当流程反复出现、用途单一且现有脚本或文档无法清楚表达时，才在 `.agents/skills/<name>/SKILL.md` 新增 repo skill；不要复制本文件或专题文档。
- 默认单 agent。只读且彼此独立的查询可并行；仅在用户明确要求时委派。
- 结束时简洁汇报实际改动、验证结果和未验证风险。

## 发布

发布规则以 `.github/workflows/release.yml`、`mdcx/consts.py::LOCAL_VERSION` 和当前 Git Tag/Release 状态为准。需要发布时再读取并核对这些实时来源。
