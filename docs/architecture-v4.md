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

网络 Cookie 和翻译服务分组内部也已经使用真实布局。新增设置控件应加入对应 `QGridLayout` / `QVBoxLayout`，不得通过扩大父控件并把后续 sibling 整体下移来“腾位置”。

NFO 自由表单等尚未完成拆分的特殊编辑器暂时走兼容路径。修改这些页面时，应先把一个完整分组迁入 Layout，再删除对应 geometry 规则，避免两套布局同时控制同一控件。

## 主题：语义 token

主题入口为 `LIGHT_TOKENS`、`DARK_TOKENS` 和 `_theme_qss()`。核心 QSS 应使用或解析为以下语义，而不是为明暗主题分别新增颜色：

- `window`、`surface`、`surface_muted`、`input_bg`、`navigation`
- `text`、`text_muted`、`text_disabled`、`on_accent`
- `border`、`accent`、`accent_hover`、`accent_pressed`
- `danger`、`warning`、`success`
- `radius_sm`、`radius_md`、`radius_lg`

新增控件样式必须同时验证亮色、暗色、disabled、focus 和 selected 状态。资源 URL 必须经 `_qss_resources()` 转换，保证源码和 PyInstaller 环境一致。

## 配置与凭据

普通配置通过 `ConfigBinder` 声明式绑定，保存使用原子替换和备份。API Key、Token 与 Cookie 通过 secret store 优先写入系统密钥库。新增设置项时至少需要：

1. Pydantic 模型和默认配置；
2. 必要的版本迁移；
3. 声明式绑定及输入 Validator；
4. load/save 往返测试；
5. 若为凭据，加入 secret 字段清单且不得出现在导出配置中。

## 质量门

提交前执行：

```powershell
uv run --locked ruff format --check
uv run --locked ruff check
uv run --locked pytest tests -q
uv run --locked python scripts/build.py --version 4.0.0
```

Windows 构建日志必须出现“冻结程序启动验证通过”。结果模型、布局或主题变更还应实际构造一次 offscreen 主窗口；仅导入模块不足以发现 Designer 控件替换和 selection model 信号问题。
