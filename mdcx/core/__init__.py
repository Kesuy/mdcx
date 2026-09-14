"""
此模块实现刮削过程的核心功能
依赖:
    此模块可依赖 models 中所有其他模块
"""

from ..base import web as _base_web
from .avwiki import get_actorname as _get_actorname

# 保持既有 translate.py 调用不变，同时把演员名查询切换到更稳健的 AV-Wiki 解析实现。
_base_web.get_actorname = _get_actorname
