# MDCx repository instructions

MDCx 是 PyQt6 本地媒体元数据工具。总原则：**用最小、可验证的改动解决当前问题，不为未来假设增加架构。**

用户请求定义任务范围。明确的改动请求直接实施；只有缺少会改变结果的关键信息，或动作不可逆、超出范围时才询问。

## 开始任务

1. 先检查当前分支和工作区状态，不覆盖已有改动。
2. 用精准搜索定位目标符号、调用方和相关测试；先读局部，证据不足再扩大范围。
3. 当前代码、测试和 workflow 是事实来源。版本号、分支、站点协议和 CI 状态等易变信息现场读取。
4. `build/`、`dist/`、虚拟环境、缓存、日志、用户数据和生成产物不是源码入口。

## 项目地图

- `main.py` 是 GUI 入口；`mdcx/controllers/` 与 `mdcx/views/` 负责 UI。
- `mdcx/core/` 负责媒体、NFO、图片和文件整理；`mdcx/crawlers/` 负责站点适配。
- `mdcx/config/` 与 `mdcx/models/` 负责配置、运行状态和领域模型。
- `tests/` 是离线回归测试；`scripts/` 与 `.github/workflows/` 是构建和发布流程的事实来源。

## 修改约束

- 不做无关重构，不顺手全仓格式化。
- 不提交敏感凭据或本地用户配置。
- 修改持久化配置、枚举、默认值或迁移时，必须兼容已有配置；确需改键时提供迁移与 round-trip 测试。
- 修改真实文件移动、重命名或整理逻辑时保持 fail-closed，不得静默覆盖。
- 修改 `.ui` 后运行 `uv run --locked python scripts/generate_ui.py` 并提交对应生成文件；不要手改生成视图绕过 Designer 源文件。
- 依赖变更通过 `uv` 更新 `uv.lock`，不要手工编辑锁文件。
- 爬虫解析变化优先增加脱敏本地 fixture；在线请求成功不能替代单元测试。
- 修复覆盖根因和直接同类路径，不扩大成无边界清理。
- 未经用户明确要求，不创建 Tag、Release，不重写 Git 历史。

## Codex 本地验证

普通改动默认只做本次改动所需的本地验证：

```bash
uv run --locked ruff format --check
uv run --locked ruff check --output-format=concise
git diff --check
uv run --locked pytest <relevant tests> -q
```

**禁止在普通发布流程中由 Codex 重复执行完整 pytest、完整本地 PyInstaller/DMG 构建或持续刷新 GitHub Actions/Release 状态。** 只有相关测试失败、改动触及构建/CI 本身、存在未解风险或用户明确要求时，才扩大本地验证。

PR 的 `CI` workflow 负责完整 pytest、Windows 构建与 smoke。**发布型 PR 的 CI 成功视为完整发布前验证**，Codex 不再在本地重复同一套全量测试与打包。

## 发布自动化

发布规则以 `.github/workflows/ci.yaml`、`.github/workflows/auto-release.yml`、`.github/workflows/release.yml`、`mdcx/consts.py::LOCAL_VERSION` 和当前 Tag/Release 状态为准。

- Codex 创建发布分支时使用 `codex/` 前缀，并在 PR 内更新 `LOCAL_VERSION`。
- `CI` 成功后，自动合并流程只接受：仓库所有者本人、同仓库分支、目标为 `master`、非 Draft、且分支名以 `codex/` 开头的 PR；外部 PR 不自动合并。
- 自动合并后创建版本 Tag，并显式触发既有 `release.yml`。正式 Release 仍必须经过其中的完整测试、Windows/macOS 构建、smoke、附件完整性检查和发布步骤。
- 普通非发布 PR 若未提升 `LOCAL_VERSION`，合并后不得重复创建旧 Tag 或重复发布。
- 自动发布中断后可在 Actions 重跑失败作业：已合并 PR 复用原合并提交；已有 Tag 必须指向该提交，才可补触发 Release。已正式发布或仍在运行的 Release 会跳过，普通未改版本的 PR 不发版。此恢复逻辑适用于包含修复的新工作流运行；旧运行使用旧版工作流，需手动触发对应 Tag 的 Release。
- 不持续轮询 CI/Release。触发后只做必要的单次状态核验；若任务仍在运行，直接报告当前状态或运行链接。

## 结束任务

简洁汇报实际改动、验证结果和未验证风险。若任务要求发布，说明版本号、PR/合并状态、Tag 与 Release 状态。
