import os
from pathlib import Path
from types import ModuleType


def showFilePath(file_path: str) -> str:
    if len(file_path) > 55:
        show_file_path = file_path[-50:]
        show_file_path = ".." + show_file_path[show_file_path.find("/") :]
        if len(show_file_path) < 25:
            show_file_path = ".." + file_path[-40:]
    else:
        show_file_path = file_path
    return show_file_path


def _is_descendant(p: str | Path, parent: str | Path, path_module: ModuleType) -> bool:
    try:
        p = path_module.realpath(os.fspath(p), strict=os.path.ALLOW_MISSING)
        parent = path_module.realpath(os.fspath(parent), strict=os.path.ALLOW_MISSING)
    except OSError:
        return False
    try:
        return path_module.commonpath([p, parent]) == str(parent)
    except (OSError, ValueError):
        return False


def is_descendant(p: str | Path, parent: str | Path) -> bool:
    """检查 p 是否是 parent 或者 parent 的后代。"""
    return _is_descendant(p, parent, os.path)


def is_any_descendant(p: str | Path, *parents: str | Path) -> bool:
    """
    检查 p 是否是 parents 中某路径的后代.
    """
    return any(is_descendant(p, parent) for parent in parents)
