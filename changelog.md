## 修复
- 修复 `MDCx.config` 指向已移动或不存在的配置时，程序在启动阶段直接崩溃的问题。
- 配置指针失效时自动选取程序当前目录中最后修改的 JSON 配置，并更新配置指针；没有候选配置时才创建默认 `config.json`。
- 停止生成已无实际作用的 `highdpi_passthrough` 空文件，并安全清理旧版留下的 0 字节标记文件。
- 修复打包脚本依赖系统 PATH 查找 PyInstaller 入口的问题，并避免 Windows GBK 终端因状态 Emoji 产生编码异常。

## 优化
- 非关键启动任务延后到首屏显示后执行，封面裁切模块改为首次使用时加载。
- 已存在于系统中的 Consolas 和 Segoe UI Emoji 不再重复注册，减少启动阶段字体载入开销。
- 中文界面优先使用 Microsoft YaHei UI，并统一主要按钮的圆角、边框、间距及明暗主题层级。
- 保留旧版 `passthrough` 配置键和 INI/JSON 配置兼容，Qt 6 继续使用非整数 DPI 缩放 PassThrough 策略。
