# MDCx 架构与维护约束

本文描述当前已落地的长期架构边界。它不是愿望清单，也不记录迁移完成度；新增和修改代码时，仅在任务涉及对应领域时参考。

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

`QTreeWidget` 不再作为生产结果列表的数据源。新增字段、状态、过滤或排序时，应修改模型或代理模型；不要在界面层维护第二份平行数据，也不要遍历 Widget 来推导业务状态。

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

- 网络协程直接用 `submit`，不得包装成 `threading.Thread → executor.run → asyncio`。
- 阻塞文件或第三方库操作用 `submit_sync`。
- UI 更新只能放在 `on_success` / `on_error` 或 Qt signal 接收端。
- 网络检测、取消状态和 JavDB/FC2CMADB/JavBus Cookie 校验由 `NetworkController` 管理；新增网络站点校验应进入该控制器。
- 同类任务使用稳定名称；重新提交同名任务会取消旧 Future，并忽略过期回调。
- 窗口退出必须调用 `QtTaskManager.shutdown()`，随后由配置管理器关闭网络客户端和共享事件循环。
- 裸 `threading.Thread` 仅允许存在于旧刮削工作线程和无完整 Qt 对象的测试兼容分支；新增主窗口功能不得使用。

## 设置页：Layout 优先

标准设置 Tab 的滚动内容由垂直布局管理顶层 `QGroupBox`。分组宽度、顺序和滚动内容高度交给 Layout 与 size hint，禁止新增固定几何补丁：

```python
child.setGeometry(...)
group.resize(...)
content.resize(...)
```

设置分组应在 Designer `.ui` 中直接声明 `QGridLayout` / `QVBoxLayout`。新增设置控件直接加入布局，不通过扩大父控件并整体移动 sibling 来“腾位置”。

## 视图组合与主窗口边界

`MDCx.ui` 只定义窗口壳与页面占位；主页、日志、网络、工具、设置、关于和 NFO 浮层分别保存在页面级 `.ui`。`scripts/generate_ui.py` 负责把这些 Designer 源文件生成对应 Python 视图，`Ui_MDCx` facade 组合并保持历史控件属性兼容。不得把页面内容重新写回壳层，也不得直接修改生成的页面 `.py`。

`MyMAinWindow` 只编排初始化、跨控制器路由和 Designer 兼容薄槽。页面初始化、主结果页交互、设置/工具槽、窗口生命周期、预览、日志和帮助逻辑应进入已有对应控制器或 mixin，而不是继续扩大主窗口类。

## 主题：语义 token

主题入口为 `LIGHT_TOKENS`、`DARK_TOKENS` 和 `_theme_qss()`。核心 QSS 应使用语义 token，而不是为明暗主题分别新增硬编码颜色。

常用语义包括：

- `window`、`surface`、`surface_muted`、`input_bg`、`navigation`
- `text`、`text_muted`、`text_disabled`、`on_accent`
- `border`、`accent`、`accent_hover`、`accent_pressed`
- `danger`、`warning`、`success`
- `radius_sm`、`radius_md`、`radius_lg`

新增控件样式需考虑亮色、暗色、disabled、focus 和 selected 状态。资源 URL 通过现有 QSS 资源转换逻辑处理，保证源码和 PyInstaller 环境一致。

设置页子控件不要用独立 `setStyleSheet()` 保存颜色。状态文字、分区标题、代码编辑器和校验信息使用现有语义属性，由页面 token QSS 统一解析。Designer `.ui` 不保存内联 `styleSheet`。

## 配置与凭据

普通配置通过现有声明式 binding 管理，保存使用原子替换和备份。API Key、Token 与 Cookie 通过 secret store 优先写入系统密钥库。

新增持久化设置通常需要：

1. Pydantic 模型和默认值；
2. 必要的旧版本迁移；
3. 对应 UI binding 与输入校验；
4. load/save 往返测试；
5. 若为凭据，加入 secret 字段清单且不得出现在普通导出配置中。

多个控件共同组成持久化列表或互斥选择时，优先复用已有 typed/composite binding。网站优先级是有序拖放数据，保留专用模型和兼容逻辑。

## 验证边界

不要把“每次修改都完整 pytest + Windows 构建”当成架构要求。验证应与改动风险匹配：

- 局部控制器 / 模型改动：Ruff + 对应测试。
- 结果模型、布局或主题改动：对应 UI 回归，必要时构造一次 offscreen 主窗口。
- 配置迁移、共享文件系统逻辑、网络基础层：扩大到对应模块完整测试。
- 构建、依赖、发布流程或正式发布：完整离线测试，并执行相关平台构建 / 冻结启动验证。

CI 和 `.github/workflows/release.yml` 是最终发布质量门的执行事实来源。