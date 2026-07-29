## 变更
- 移除 FC2CMADB 自动登录和自动获取 Cookie 功能；设置页恢复为仅支持用户手动填写并检查 Cookie。
- 移除 Cookie 失效后的浏览器自动重新登录；刮削失败时会直接提示用户更新手动 Cookie。
- 保留 FC2CMADB Cookie 检查、数据刮削，以及服务端响应 Cookie 更新并保存的现有行为。

## 构建
- 移除 Playwright 依赖以及 Edge/Chrome 浏览器自动化代码，降低 Windows EXE 和 macOS DMG 的打包体积。
