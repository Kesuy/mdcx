import ast
import re
from collections.abc import Sequence

_LEGACY_VERSION_RE = re.compile(r"^220\d+(?:\.\d+)?$")
_SEMANTIC_VERSION_RE = re.compile(r"^(\d+(?:\.\d+)+)$")


def parse_version(version: object) -> tuple[int, tuple[int, ...]] | None:
    """Parse MDCx versions while treating the 3.x line as newer than legacy date tags."""
    text = str(version or "").strip()
    if _LEGACY_VERSION_RE.fullmatch(text):
        base, _, suffix = text.partition(".")
        parts = (int(base), int(suffix)) if suffix else (int(base),)
        return 0, parts

    match = _SEMANTIC_VERSION_RE.fullmatch(text)
    if not match:
        return None
    return 1, tuple(int(part) for part in match.group(1).split("."))


def extract_local_version(source: str) -> str | None:
    """Read the complete LOCAL_VERSION literal without accepting a valid prefix of an invalid value."""
    try:
        module = ast.parse(source)
    except SyntaxError:
        return None

    for statement in module.body:
        if not isinstance(statement, ast.Assign) or len(statement.targets) != 1:
            continue
        target = statement.targets[0]
        if not isinstance(target, ast.Name) or target.id != "LOCAL_VERSION":
            continue
        value = statement.value.value if isinstance(statement.value, ast.Constant) else None
        if isinstance(value, bool) or not isinstance(value, (str, int)):
            return None
        version = str(value).strip()
        return version if parse_version(version) is not None else None
    return None


def _pad(parts: Sequence[int], length: int) -> tuple[int, ...]:
    return tuple(parts) + (0,) * (length - len(parts))


def compare_versions(left: object, right: object) -> int | None:
    left_parsed = parse_version(left)
    right_parsed = parse_version(right)
    if left_parsed is None or right_parsed is None:
        return None

    left_generation, left_parts = left_parsed
    right_generation, right_parts = right_parsed
    if left_generation != right_generation:
        return 1 if left_generation > right_generation else -1

    length = max(len(left_parts), len(right_parts))
    left_normalized = _pad(left_parts, length)
    right_normalized = _pad(right_parts, length)
    return (left_normalized > right_normalized) - (left_normalized < right_normalized)


def is_newer_version(candidate: object, current: object) -> bool:
    comparison = compare_versions(candidate, current)
    return comparison is not None and comparison > 0
