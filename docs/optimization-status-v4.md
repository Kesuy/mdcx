# MDCx 4.x 优化完成度

本文把 4.0 静态审计建议映射到可验证的代码状态。状态只使用“完成 / 部分完成 / 待处理”，避免把过渡层误报为最终架构。

## 安全与发布基础

| 项目 | 状态 | 当前实现与验收 |
|---|---|---|
| HTTPS 默认验证、自定义 CA | 完成 | 爬虫和 LLM 共用安全配置；关闭验证必须显式选择不安全模式。 |
| 移除 OpenSSL 1.1 DLL | 完成 | 仓库和冻结产物均不再携带旧 DLL；构建验收检查归档。 |
| pytest 接入 CI/Release | 完成 | CI 和发布构建均运行完整 pytest，构建依赖测试通过。 |
| 原子配置写入与备份恢复 | 完成 | 临时文件、flush/fsync、replace 和有效备份恢复集中在配置 I/O 层。 |
| 密钥和 Cookie 系统密钥库 | 完成 | 敏感字段优先保存到 keyring；JSON 不再作为首选秘密存储。 |
| 单一版本源与旧文档清理 | 完成 | `mdcx/consts.py` 驱动包元数据、构建和发布，当前版本为 4.0.1。 |
| Windows 冻结启动可靠性 | 完成 | 构建过滤冲突 ICU，真实启动 `--smoke-test`；测试 FFmpeg 不进入 EXE。 |

## 网络、依赖与 LLM

| 项目 | 状态 | 当前实现与验收 |
|---|---|---|
| 统一网络指纹 | 完成 | 旧随机请求头入口兼容转发至统一指纹源，TLS 与 HTTP 头保持一致。 |
| curl-cffi / OpenAI SDK 升级 | 完成 | 依赖已升级并锁定，测试覆盖主要调用路径。 |
| LLM Provider Adapter | 完成 | OpenAI Responses 与第三方 OpenAI-compatible Chat Completions 分层。 |

## UI 与交互

| 项目 | 状态 | 当前实现与验收 |
|---|---|---|
| 880px 逻辑宽度与断点 | 完成 | 窄屏折叠导航，详情/结果改为上下排列。 |
| 结果 Model/View | 完成 | `QTreeView + QAbstractItemModel + QSortFilterProxyModel`，支持搜索、状态筛选和排序。 |
| 结果页独立组件 | 完成 | 结果工具栏和列表由 `ResultPanel` 管理，并测试真实 QSS 下的文字可读区域。 |
| NFO 编辑器布局 | 完成 | 固定坐标画布已替换为可滚动表单布局。 |
| 设置搜索、基础/高级分层 | 完成 | 设置控制器提供搜索索引和级别过滤。 |
| 设置页全面声明式布局 | 部分完成 | 标准分组、网络、翻译等已迁移；巨型生成 UI 内仍有兼容页面使用绝对坐标。 |
| 拆分巨型 `MDCx.ui` / `MDCx.py` | 部分完成 | ResultPanel、SettingsPageController、NFO 布局等已独立；生成视图尚未按页面完全拆开。 |
| 主题 token 全面收口 | 部分完成 | 核心明暗色使用语义 token；旧页面仍有硬编码 QSS。 |
| 输入验证全面覆盖 | 部分完成 | 新绑定字段已使用 validator；旧保存路径仍有少量容错转换。 |
| 安全快捷键 | 完成 | 单字母全局快捷键已替换；删除操作要求结果列表焦点。 |

## 控制器与后台任务

| 项目 | 状态 | 当前实现与验收 |
|---|---|---|
| Qt TaskManager 与显式 shutdown | 完成 | 主窗口后台入口统一调度，退出时取消任务并关闭后台执行器。 |
| 清理主窗口裸 `threading.Thread` | 完成 | 主窗口不再创建临时线程；现有刮削工作线程仅保留协作式停止与有界等待。 |
| 主窗口职责拆分 | 部分完成 | 结果、设置、任务和网络控制器已拆出；刮削、NFO 和文件操作仍有代码位于主窗口类。 |
| 配置声明式绑定 | 部分完成 | 已有通用 binding schema 并覆盖新增/高风险字段；旧 load/save 仍需逐页迁移。 |

## 后续顺序

1. 按页面拆分生成 UI，优先网络、NFO、工具页，逐步删除 `responsive_layout.py` 的兼容 geometry 路径。
2. 抽出 `NfoController`、`FileController`，继续缩小 `MyMAinWindow`。
3. 将剩余配置字段迁移到 binding schema，并补齐范围 validator 和行内错误提示。
4. 把剩余硬编码 QSS 收敛到主题 token。
5. 实现 NFO 保存前 diff、文件操作 dry-run、失败原因分类/一键重试和可访问性审计。

每轮修改必须通过完整 pytest、Ruff、格式检查；Windows 发布产物还必须通过冻结启动和 DLL 归档检查。
