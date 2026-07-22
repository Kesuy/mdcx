## 修复
- 修复 AVSOX 改版为 SPA 后，旧版 HTML/XPath 刮削无法获取搜索和详情数据的问题。
- 改用 AVSOX 当前公开 JSON API，恢复标题、演员、标签、简介、发行日期、时长、制作商和封面等信息的获取。
- 修复 `H4610`、`H0930` 等番号尾号只有 3 位时识别不完整的问题。
- 支持直接指定新版 AVSOX 详情页 URL 进行刮削。

## 已验证样例
- `H4610-ori696` — https://avsox.click/cn/movies/nrzebvn
- `H4610-ori641` — https://avsox.click/cn/movies/nbwxgek
- `H0930-gol065` — https://avsox.click/cn/movies/krzjegk
