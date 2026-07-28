## 优化
- 设置 → 网络中的 Cookie 配置现在按 JavDB、JavBus、FC2CMADB 分区显示，FC2CMADB 的认证方式和登录控件归属更清晰。
- FC2CMADB 自动登录会在 Cloudflare 验证先于登录表单出现时保持浏览器打开，等待用户完成验证后再自动填写并提交账号信息。

## 修复
- 修复启动或打开设置时自动检测 JavDB、JavBus Cookie 并产生不必要网络请求的问题；Cookie 现在仅在用户主动点击检查时验证。
- 修复 JavBus Cookie 为空仍可能显示“连接正常”的误导状态；空内容现在直接提示未填写且不会访问网络。
- 修复 FC2CMADB 登录页出现 Cloudflare 验证时，Playwright 等待不到登录输入框并提前关闭 Edge 的问题。
