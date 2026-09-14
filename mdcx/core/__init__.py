"""
此模块实现刮削过程的核心功能
依赖:
    此模块可依赖 models 中所有其他模块
"""

from ..base import web as _base_web
from . import translate as _translate
from .avwiki import get_actorname as _get_actorname

# 同时覆盖旧模块入口和 translate.py 已绑定的函数对象，避免打包后的导入顺序导致旧解析器继续被调用。
_base_web.get_actorname = _get_actorname
_translate.get_actorname = _get_actorname
