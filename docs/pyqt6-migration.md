# PyQt6 迁移记录

## 背景

桌面端已经完成 PyQt5/Qt5 到 PyQt6 的迁移。本文件保留迁移背景、兼容差异和验证清单，供维护历史与回归排查使用。

## PyQt6 主要差异

- `PyQt5` 包名迁移为 `PyQt6`。
- Qt 枚举和 Flag 采用标准 Python `Enum`/`Flag`，需要使用完整命名空间，例如 `Qt.AlignmentFlag.AlignCenter`、`QMessageBox.StandardButton.Yes`。
- `exec_()` 已移除，统一改为 `exec()`。
- `QAction` 从 `QtWidgets` 迁移到 `QtGui`。
- Qt6 默认启用高 DPI 缩放，Qt5 中的 `AA_EnableHighDpiScaling`、`AA_UseHighDpiPixmaps` 不再适合继续保留。
- `pyrcc6` 不再提供，资源建议继续使用现有文件路径加载方式。

## 第一阶段范围

第一阶段目标是完成 PyQt6 基线迁移，并做低风险的 UI 统一优化：

- 更新依赖到 PyQt6。
- 更新 `pyuic` 脚本并重新生成 UI 文件。
- 迁移手写 Qt API、枚举、消息框、菜单、文件选择器等 PyQt6 不兼容用法。
- 调整启动入口中的高 DPI 初始化。
- 保持现有页面结构和业务流程不变。
- 优化样式层的统一性，包括基础控件边框、按钮 hover/pressed、输入框焦点态、工具提示和列表选中态。

## 4.0 后续维护

- 增加主题策略：跟随系统、浅色、深色。
- 接入 `QGuiApplication.styleHints().colorScheme()`，监听系统主题变化。
- 将图标颜色、日志面板、弹窗和设置页统一到可维护的调色板。
- 针对 Windows 100%/150%/175%、macOS Retina、多显示器分别验证。
- 主页面、日志页和设置页已由布局控制器接管；新增页面应采用独立 controller 和 Qt Layout，避免增加运行时坐标修补。

## 第二阶段进展

- 已增加浅色/暗色主题 token，并以统一入口刷新 `QApplication` palette，避免系统暗色或系统强调色污染未开启暗色模式时的弹窗、菜单和选择态。
- 已统一概览页树控件的 hover、选中、非活动选中和 branch 样式，避免 Qt6/Fusion 原生选择色导致文字不可读。
- 已统一主界面右键菜单、托盘菜单和裁剪弹窗的主题样式。
- 已补充复选框、单选框、滑块、滚动条、小型说明按钮等控件的基础状态样式。
- 已继续修复 PyQt6 短枚举遗漏，包括 `QItemSelectionModel.SelectionFlag.NoUpdate`、`QEvent.Type.Wheel`、`QMessageBox.Icon.Information`。
- 已在启动入口固定使用 Fusion + 应用自有 palette，未开启暗色模式时默认使用浅色主题，避免系统暗色模式导致弹窗变暗。
- 已监听系统主题变化并重新应用 MDCx 当前主题，避免运行中主题漂移。
- 已修复裁剪窗口拖拽相关 Qt6 鼠标事件 API，统一使用 `position()` / `globalPosition()`。
- 已为日志面板链接增加浅色/暗色文档级样式，提升 URL 在日志输出中的可读性。

## 验证清单

- `ruff format`
- `ruff check`
- 应用可正常启动主窗口。
- 托盘菜单：显示、隐藏、退出。
- 主界面右键菜单。
- 刮削启动、停止、删除、保存等确认弹窗。
- 文件选择器。
- 海报裁剪窗口。
- NFO 编辑窗口。
- 封面、缩略图在高 DPI 下清晰且比例正确。
