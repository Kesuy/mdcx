# MDCx 4.x 架构与维护约束

本文描述 4.x 已落地的架构边界。它不是愿望清单，而是新增和修改代码必须遵守的约束；对应回归测试位于 `tests/controllers` 与 `tests/test_task_manager.py`。

## 结果列表：Model/View

生产主窗口的结果列表由 `ResultTreeView`、`ResultTreeModel` 和 `ResultFilterProxyModel` 组成：

```text
ShowData 字典
    ↓
ResultTreeModel (QAbstractItemModel)
    ↓
ResultFilterProxyModel (QSortFilterProxyModel)
    ↓
ResultTreeView (QTreeView)
```

`QTreeWidget` 只保留给轻量单元测试兼容层，不得再作为生产结果列表的数据源。新增字段、状态、过滤或排序时，应修改模型或代理模型；不要在界面层维护第二份平行数据，也不要遍历 Widget 来推导业务状态。

批量操作必须从选择模型取得当前条目，并继续排除“成功/失败”分类节点。删除或重排条目后必须由模型发出更新，不能直接操作 Qt 内部私有 model。

## 后台任务：统一 TaskManager

主窗口发起的版本检查、Cookie 检测、网络检测、打开文件和媒体移动统一提交给 `QtTaskManager`：

```text
Qt 主线程
    ↓ submit / submit_sync
QtTaskManager
    ↓
AsyncBackgroundExecutor
    ↓
完成/失败信号回到 Qt 主线程
```

约束如下：

- 网络协程直接用 `submit`，不得包装成 `threading.Thread → executor.run → asyncio`。
- 阻塞文件或第三方库操作用 `submit_sync`。
- UI 更新只能放在 `on_success` / `on_error` 或 Qt signal 接收端。

网络检测、取消状态和 JavDB/FC2CMADB/JavBus Cookie 校验由 `NetworkController` 独立管理。主窗口只保留 Qt Designer 信号所需的薄槽函数；新增网络站点校验应进入该控制器，不得把请求、解析或任务状态重新写回 `MyMAinWindow`。
- 同类任务使用稳定名称；重新提交同名任务会取消旧 Future，并忽略过期回调。
- 窗口退出必须调用 `QtTaskManager.shutdown()`，随后由配置管理器关闭网络客户端和共享事件循环。
- 裸 `threading.Thread` 仅允许存在于旧刮削工作线程和无完整 Qt 对象的测试兼容分支；新增主窗口功能不得使用。

## 设置页：Layout 优先

标准设置 Tab 的滚动内容由垂直布局管理顶层 `QGroupBox`。分组宽度、顺序和滚动内容高度交给 Layout 与 size hint，禁止新增下列补丁：

```python
child.setGeometry(...)
group.resize(...)
content.resize(...)
```

所有设置分组（包括网络 Cookie、翻译服务和 NFO 设置）都必须在 `settings_page.ui` 中直接声明 `QGridLayout` / `QVBoxLayout`。分组直接子控件不得保存 geometry，控制器也不得在启动时把坐标重新包装成布局；新增设置控件必须直接加入 Designer 布局，不得通过扩大父控件并把后续 sibling 整体下移来“腾位置”。

## 视图组合与主窗口边界

`MDCx.ui` 只定义窗口壳与页面占位；主页、日志、网络、工具、设置、关于和 NFO 浮层分别保存在页面级 `.ui`。`scripts/split_main_ui.py` 一次生成壳层及全部页面 Python 模块，`Ui_MDCx` facade 负责组合并保持历史控件属性兼容。不得把页面内容重新写回壳层，也不得直接修改生成的页面 `.py`。

`MyMAinWindow` 只编排初始化、跨控制器路由和 Designer 兼容薄槽。页面初始化、主结果页交互、设置/工具槽分别由 `PageSetupMixin`、`MainPageMixin` 和 `SettingsToolSlotsMixin` 承担；窗口生命周期与导航、媒体预览、日志视图、帮助/提示分别由 `WindowLifecycleMixin`、`PreviewControllerMixin`、`LogControllerMixin` 和 `HelpControllerMixin` 承担。页面新增行为应进入对应控制器，而不是继续扩大主窗口类。

## 主题：语义 token

主题入口为 `LIGHT_TOKENS`、`DARK_TOKENS` 和 `_theme_qss()`。核心 QSS 应使用或解析为以下语义，而不是为明暗主题分别新增颜色：

- `window`、`surface`、`surface_muted`、`input_bg`、`navigation`
- `text`、`text_muted`、`text_disabled`、`on_accent`
- `border`、`accent`、`accent_hover`、`accent_pressed`
- `danger`、`warning`、`success`
- `radius_sm`、`radius_md`、`radius_lg`

新增控件样式必须同时验证亮色、暗色、disabled、focus 和 selected 状态。资源 URL 必须经 `_qss_resources()` 转换，保证源码和 PyInstaller 环境一致。

设置页子控件不得调用 `setStyleSheet()` 保存独立颜色。状态文字、分区标题、代码编辑器和校验信息使用 `statusRole`、`sectionTitle`、`cookieEditor`、`validationError` 等语义属性，由页面 token QSS 统一解析。

所有 Designer `.ui` 禁止保存 `styleSheet` 属性；`scripts/split_main_ui.py` 在生成前移除残留样式并把旧设置页颜色意图迁移为 `semanticRole`。窗口按钮、进度条及裁切预览等特殊控件同样由主题构建器或 Palette 管理。

## 配置与凭据

普通配置通过 `ConfigBinder` 声明式绑定，保存使用原子替换和备份。API Key、Token 与 Cookie 通过 secret store 优先写入系统密钥库。新增设置项时至少需要：

1. Pydantic 模型和默认配置；
2. 必要的版本迁移；
3. 声明式绑定及输入 Validator；
4. load/save 往返测试；
5. 若为凭据，加入 secret 字段清单且不得出现在导出配置中。

多个控件共同组成一个持久化列表或互斥选择时，使用 `CompositeBinding` 及 `settings_composites.py` 中的 typed schema。NFO、Emby、水印和总开关不得在 `load_config.py` / `save_config.py` 中重新手工拼装；定时器、主题和托盘等加载副作用继续留在流程控制器中。网站优先级是有序拖放数据，保留专用模型和兼容逻辑。

## 质量门

提交前执行：

```powershell
uv run --locked ruff format --check
uv run --locked ruff check
uv run --locked pytest tests -q
uv run --locked python scripts/build.py --debug
```

Windows 构建日志必须出现“冻结程序启动验证通过”。结果模型、布局或主题变更还应实际构造一次 offscreen 主窗口；仅导入模块不足以发现 Designer 控件替换和 selection model 信号问题。
