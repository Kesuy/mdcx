# MDCx

![python](https://img.shields.io/badge/Python-3.13-3776AB.svg?style=flat&logo=python&logoColor=white)

MDCx 是使用 PyQt6 开发的本地媒体元数据整理工具，支持多站点刮削、图片/NFO 处理、命名整理、字幕与媒体服务器辅助功能。

## 下载

请从 [Kesuy/mdcx Releases](https://github.com/Kesuy/mdcx/releases) 下载 Windows 或 macOS 构建。4.0 起要求现代操作系统与 Python 3.13；不再支持 Windows 7 / Python 3.8 构建线。

## 从源码运行

```bash
uv sync --locked --all-extras --dev
uv run --locked python main.py
```

运行质量门：

```bash
uv run --locked ruff format --check
uv run --locked ruff check
uv run --locked pytest tests -q
```

测试配置已固化：`uv.toml` 将缓存放在项目可写目录，pytest 使用系统分配的隔离临时目录、Qt offscreen 和离线模型模式；锁定的开发依赖自带 FFmpeg，因此不要求系统预装 FFmpeg 或启用 Windows Developer Mode。开发 FFmpeg 仅由测试配置注入，不会打进正式 EXE。

Windows 打包前请阅读 [构建与排障指南](docs/build-troubleshooting.md)。构建脚本会实际启动冻结产物并检查 Qt 与完整启动导入树；验收未通过时不会把文件视为成功产物。

界面、后台任务和配置扩展须遵循 [架构与维护约束](docs/architecture.md)，其中记录了 Model/View 结果列表、统一 TaskManager、设置页布局和主题 token 的长期边界。

## 安全说明

- HTTPS 证书校验默认开启；特殊代理环境可在“设置 > 网络”指定 PEM 格式自定义 CA。
- API Key、Token 与 Cookie 在系统密钥库可用时保存到 Windows Credential Manager、macOS Keychain 或 Linux Secret Service；无可用后端时为保持便携兼容，会回退到原配置文件。
- 导出或分享配置前仍建议人工检查内容，不要公开 Cookie、Token 或日志中的私人路径。

## 上游项目

- [yoshiko2/Movie_Data_Capture](https://github.com/yoshiko2/Movie_Data_Capture)
- [moyy996/AVDC](https://github.com/moyy996/AVDC)
- [sqzw-x/mdcx](https://github.com/sqzw-x/mdcx)

感谢历代维护者和贡献者。

## 授权许可

本项目按 GNU General Public License v3.0（GPLv3）许可发布。使用、修改和分发须遵守 `LICENSE` 中的许可条款及当地法律法规，使用者自行承担使用后果。
