import ntpath
import posixpath
from pathlib import PurePosixPath, PureWindowsPath

import pytest

from mdcx.utils.path import _is_descendant


@pytest.mark.parametrize(
    "p, parent, expected",
    [
        # Basic cases
        ("/a/b/c", "/a/b", True),
        ("/a/b/c", "/a/b/./", True),
        ("/a/b", "/a/b", True),
        ("/a/b", "/a/b/", True),
        ("/a/b", "/a/b/.", True),
        ("/a/c", "/a/b", False),
        ("/a/b", "/a/b/c", False),
        ("/a/b/../c", "/a", True),
        ("/a/b/../c", "/a/c", True),
        ("/a/b/.", "/a/b", True),
        # Relative paths
        ("a/b/c", "a/b", True),
        ("a/b", "a/b", True),
        ("a/c", "a/b", False),
        ("a/c", "a/b/..", True),
        # Path objects
        (PurePosixPath("/a/b/c"), PurePosixPath("/a/b"), True),
        (PurePosixPath("a/b/c"), PurePosixPath("a/b"), True),
        # Edge cases
        ("/a/barbar", "/a/bar", False),
        ("/a/bar", "/a/barbar", False),
        ("/", "/", True),
        ("/..", "/", True),
        ("/a", "/", True),
        # Mixed types
        (PurePosixPath("/a/b/c"), "/a/b", True),
        ("/a/b/c", PurePosixPath("/a/b"), True),
    ],
)
def test_is_descendant_posix(p, parent, expected):
    assert _is_descendant(p, parent, posixpath) == expected


@pytest.mark.parametrize(
    "p, parent, expected",
    [
        ("C:\\Users\\Test", "C:\\Users", True),
        ("C:\\Users\\Test", "C:\\", True),
        ("C:\\Users\\Test", "D:\\Users", False),
        ("C:\\Users\\Test\\", "C:\\Users", True),
        ("C:\\Users\\Test", "C:\\Users\\", True),
        ("C:/Users/Test", "C:/Users", True),
        (PureWindowsPath("C:/Users/Test"), PureWindowsPath("C:/Users"), True),
        (PureWindowsPath("C:/Users/Test"), "C:/Users", True),
        ("C:/Users/Test", PureWindowsPath("C:/Users"), True),
    ],
)
def test_is_descendant_windows(p, parent, expected):
    assert _is_descendant(p, parent, ntpath) == expected
