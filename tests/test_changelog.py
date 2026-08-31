import subprocess
from pathlib import Path

import pytest
import typer

from scripts.changelog import generate_changelog, get_commit_log_for_head_tag, get_latest_tag


def test_generate_changelog_groups_chinese_release_notes_and_omits_empty_categories(tmp_path: Path):
    output = tmp_path / "changelog.md"

    generate_changelog(
        "\n".join(
            [
                "abc1234 feat: 新增同番号本地图片整理",
                "def5678 perf: 优化本地图片格式转换",
                "61cd615 fix: refresh fc2cmadb sessions and images",
                "987abcd docs: update readme",
            ]
        ),
        output,
    )

    assert (
        output.read_text(encoding="utf-8") == "## 新功能\n"
        "- 新增同番号本地图片整理\n\n"
        "## 优化\n"
        "- 优化本地图片格式转换\n\n"
        "## 修复\n"
        "- 修复 FC2CMADB 会话续期、演员数据与图片下载处理\n"
    )


def test_generate_changelog_uses_curated_chinese_notes_and_removes_empty_sections(tmp_path: Path):
    output = tmp_path / "changelog.md"
    curated = """## 新功能
- 新增图片整理开关

## 优化

## 修复
- 修复图片下载问题
"""

    generate_changelog("abc1234 feat: 新增图片整理开关", output, curated_content=curated)

    assert output.read_text(encoding="utf-8") == ("## 新功能\n- 新增图片整理开关\n\n## 修复\n- 修复图片下载问题\n")


def test_generate_changelog_selects_versioned_release_and_maps_categories(tmp_path: Path):
    output = tmp_path / "release.md"
    curated = """## 4.0.2

### 工程
- 修复版本化发布说明生成

## 4.0.1

### 修复
- 旧版本说明不应重复出现
"""

    generate_changelog(
        "abc1234 fix: 修复版本化发布说明生成",
        output,
        curated_content=curated,
        curated_version="4.0.2",
    )

    assert output.read_text(encoding="utf-8") == "## 优化\n- 修复版本化发布说明生成\n"


def test_generate_changelog_accepts_compound_curated_categories(tmp_path: Path):
    output = tmp_path / "release.md"
    curated = """## 4.0.7

### 界面与架构
- 设置页使用原生布局

### 依赖与工程
- 升级存在安全告警的依赖
"""

    generate_changelog(
        "abc1234 fix: 修复发布说明生成",
        output,
        curated_content=curated,
        curated_version="4.0.7",
    )

    assert output.read_text(encoding="utf-8") == ("## 优化\n- 设置页使用原生布局\n- 升级存在安全告警的依赖\n")


def test_generate_changelog_rejects_empty_release(tmp_path: Path):
    with pytest.raises(typer.Exit):
        generate_changelog("\n", tmp_path / "changelog.md")


def test_release_log_uses_previous_first_parent_tag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    repo = tmp_path / "repo"
    repo.mkdir()

    def git(*args: str) -> None:
        subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)

    git("init", "-b", "master")
    git("config", "user.name", "MDCx Test")
    git("config", "user.email", "mdcx@example.invalid")

    def commit(message: str, filename: str = "history.txt") -> None:
        marker = repo / filename
        marker.write_text(marker.read_text() + message + "\n" if marker.exists() else message + "\n")
        git("add", filename)
        git("commit", "-m", message)

    commit("base")
    git("tag", "220260725")
    git("branch", "prerelease")
    commit("already released on main", "main.txt")
    git("tag", "220260726")
    git("checkout", "prerelease")
    commit("side fix", "side.txt")
    git("tag", "220260726.1")
    git("checkout", "master")
    git("merge", "--no-ff", "prerelease", "-m", "release merge")
    git("tag", "220260727")

    monkeypatch.chdir(repo)
    log = get_commit_log_for_head_tag("220260727", "220*")

    assert "already released on main" not in log
    assert "side fix" in log
    assert "release merge" in log


def test_latest_tag_uses_nearest_release_instead_of_numeric_sort(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    repo = tmp_path / "repo"
    repo.mkdir()

    def git(*args: str) -> None:
        subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)

    git("init", "-b", "master")
    git("config", "user.name", "MDCx Test")
    git("config", "user.email", "mdcx@example.invalid")
    marker = repo / "history.txt"
    marker.write_text("legacy\n", encoding="utf-8")
    git("add", "history.txt")
    git("commit", "-m", "legacy release")
    git("tag", "220260801")
    marker.write_text("legacy\nsemantic\n", encoding="utf-8")
    git("commit", "-am", "semantic release")
    git("tag", "3.0")

    monkeypatch.chdir(repo)

    assert get_latest_tag("[0-9]*") == "3.0"
