## 新功能
- 在主界面编辑 NFO 信息并点击“保存”后，自动按当前目录和文件命名设置重新整理已刮削影片。
- 支持整体迁移单影片目录，视频、NFO 及同名前缀的关联文件会同步重命名，`fanart.jpg`、`poster.jpg`、`thumb.jpg` 等固定名称素材保持不变。
- 自动同步主界面文件路径、封面路径和成功记录，并清理空的旧演员目录。
- 为防止误覆盖，目标目录已存在或源目录包含多个主影片时只保存 NFO 信息，不执行自动迁移。

## 热修复
- 修复 AVSOX 自定义 URL 带语言路径（例如 `https://avsox.click/cn`）时，API 被错误拼接为 `/cn/javu/data/api/...` 并返回 HTTP 400 的问题。
- 统一从配置 URL 提取站点 origin，确保批量刮削与手动刮削使用相同的正确 API 根路径。

## 修复
- 修复 AVSOX 改版为 SPA 后，旧版 HTML/XPath 刮削无法获取搜索和详情数据的问题。
- 改用 AVSOX 当前公开 JSON API，恢复标题、演员、标签、简介、发行日期、时长、制作商和封面等信息的获取。
- 修复 `H4610`、`H0930` 等番号尾号只有 3 位时识别不完整的问题。
- 支持直接指定新版 AVSOX 详情页 URL 进行刮削。

## 已验证样例
- `H4610-ori696` — https://avsox.click/cn/movies/nrzebvn
- `H4610-ori641` — https://avsox.click/cn/movies/nbwxgek
- `H0930-gol065` — https://avsox.click/cn/movies/krzjegk
