## 4.0.2

### 工程
- 修复 Release changelog 将版本标题误判为分类的问题；发布任务会按目标标签提取对应版本段。

## 4.0.1

### 工程
- 修复 Ubuntu GitHub Actions 缺少 `libEGL.so.1` 导致 PyQt6 测试无法收集的问题；CI 与 Release 测试任务会安装最小 Qt EGL 运行库。

## 4.0.0

### 安全
- 默认启用 HTTPS 证书校验，支持自定义 CA；LLM 与爬虫统一遵循该设置。
- API Key、Token 和 Cookie 优先迁移至操作系统密钥库；配置采用原子写入和有效备份恢复。
- 移除发布包中的 OpenSSL 1.1 DLL 及整目录透传。

### 架构
- 增加统一 Qt 异步任务管理器、显式后台事件循环关闭和 LLM Provider Adapter。
- 结果列表迁移至 `QTreeView + QAbstractItemModel + QSortFilterProxyModel`，保留多选、搜索、状态过滤和稳定排序。
- 版本检查、Cookie 检测和媒体移动统一由 TaskManager 调度；异步网络检查不再经过同步阻塞包装层。
- 网络检测移除最后的 `threading.Thread → Future.result()` 兼容链，生产路径只通过 TaskManager 调度和回传 Qt 状态。
- 主窗口不再创建临时裸线程；版本信息、停止流程、文件/目录打开、媒体移动和 Cookie 检测均统一使用具名 TaskManager 任务。
- 网络检测、取消状态和 JavDB/FC2CMADB/JavBus Cookie 校验拆入独立 `NetworkController`，主窗口只保留 UI 槽函数。
- OpenAI 官方端点支持 Responses API，第三方 OpenAI-compatible 服务继续使用 Chat Completions。
- 网络请求头统一由浏览器指纹模块生成；配置升级至 v4，并将旧 `website_single` 迁移为 `selected_site`。
- 网络设置改为声明式绑定，新增输入验证、设置搜索和基础/高级分层。

### 界面
- 安全快捷键替换单字母全局快捷键，删除操作仅在结果列表聚焦时生效。
- 主窗口最低逻辑宽度降至 880，窄屏自动折叠导航并将详情与结果上下排列。
- 结果列表新增搜索、状态过滤和现有排序组合。
- 结果区拆为独立 `ResultPanel` 组件；工具栏使用搜索/清空与筛选/排序两行，并按真实 QSS 的文字绘制需求保留最小宽度，加入防重叠与内部文字可读性回归测试。
- NFO 编辑器从固定 752×1300 绝对坐标画布迁移为可滚动表单布局，字段会随窗口宽度伸缩。
- 网络 Cookie 与翻译设置组改由真实 Qt Layout 管理；大多数标准设置页顶层分组不再依赖运行时 x/y/width 修补。
- 核心明暗 QSS 通过语义主题 token 解析，新增前景、输入、导航、状态色和圆角 token。

### 工程
- `LOCAL_VERSION` 成为包元数据、构建和发布的单一版本源，版本升级至 4.0.0。
- CI 与 Release 均在构建前运行完整 pytest；PR 的新提交会重新触发检查。
- 升级 curl-cffi 0.16.1、OpenAI SDK 3.5.0，并加入 keyring。
- 固化 uv/pytest 离线测试环境与 FFmpeg 工具链，Windows 无需管理员 symlink 权限也能执行完整安全测试；全套测试不再以平台条件跳过。
- 修复 Windows 冻结程序因 PATH 中第三方 ICU DLL 污染而无法导入 QtCore；构建现在剔除不兼容 ICU、执行冻结程序启动验收，并避免将测试专用 FFmpeg 打入 EXE。
