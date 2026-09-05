# 开发指南

## 环境准备

需要 Python 版本和依赖以 `pyproject.toml` / `uv.lock` 为准，并安装 [uv](https://docs.astral.sh/uv/)。

```bash
git clone https://github.com/Kesuy/mdcx.git
cd mdcx
uv sync --locked --all-extras --dev
uv run --locked pre-commit install
```

启动 GUI：

```bash
uv run --locked python main.py
```

## 验证

先运行与改动最相关的测试；涉及共享配置、文件整理、网络基础层、构建或发布时再扩大范围。完整发布前验证由 CI / Release workflow 负责兜底。

```bash
uv run --locked ruff format --check
uv run --locked ruff check
uv run --locked pytest <相关测试> -q
# 需要完整回归时：
uv run --locked pytest tests -q
```

不要为了低风险、可逆改动增加只复述实现的测试；修复回归和高风险边界应增加能真实覆盖失败条件的测试。

## 添加或修改配置

- 当前配置模型：`mdcx/config/models.py`
- 配置管理与持久化：`mdcx/config/manager.py`、`mdcx/config/io.py`
- 旧配置迁移：`mdcx/config/v1.py`、`mdcx/config/migrations.py`
- 设置页绑定：`mdcx/controllers/main_window/config_binding.py` 及相关 typed binding

运行时代码通过：

```python
from mdcx.config.manager import manager

value = manager.config.<key>
```

修改持久化字段时必须考虑旧 INI/JSON，并补迁移或 round-trip 测试；不要要求用户删除旧配置才能升级。

## 修改图形界面

`mdcx/views/` 已拆分为主壳和页面级 `.ui`。应修改 Designer 源文件，不要直接编辑对应的生成 `.py`。

修改 `.ui` 后运行：

```bash
uv run --locked bash scripts/pyuic.sh
```

主窗口行为按职责放在 `mdcx/controllers/main_window/` 的对应控制器 / mixin 中，不要重新把逻辑堆回 `main_window.py`。持久架构边界见 `docs/architecture-v4.md`。

## 目录概览

```text
mdcx/
├── mdcx/
│   ├── config/        # 配置、迁移、凭据
│   ├── controllers/   # Qt 控制器
│   ├── core/          # 媒体/NFO/图片/整理核心逻辑
│   ├── crawlers/      # 站点适配
│   ├── models/        # 领域与运行状态
│   ├── utils/         # 共享工具
│   └── views/         # Designer 源文件与生成视图
├── scripts/           # 生成、构建、版本、发布辅助脚本
├── tests/             # 离线回归测试
└── .github/workflows/ # CI / Release
```

提交前避免无关重构、全仓格式化和本地配置/密钥进入 diff。更完整的 Agent 约束见 `AGENTS.md`。
