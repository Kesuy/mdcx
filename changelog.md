## 新功能
- FC2CMADB 自动登录现在优先调用系统已安装的 Microsoft Edge，未安装时自动改用 Google Chrome。
- Windows 与 macOS 安装包内置 Playwright 控制组件，用户无需另外安装 Python、Playwright 或 Chromium。

## 优化
- 自动登录沿用 MDCx 当前代理配置，使浏览器登录与后续 Cookie 验证保持一致的网络出口。
- 登录按钮明确显示浏览器选择顺序；未检测到 Edge 或 Chrome 时给出可操作的提示。
- 用户名和密码仍仅在当前进程内存中使用，密码输入后立即清除，不写入配置或日志。

## 修复
- 修复 3.1 安装包中 FC2CMADB 自动登录因缺少 Playwright 控制组件而无法启动浏览器的问题。
