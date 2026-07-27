import subprocess
from pathlib import Path

import pytest
import typer

from scripts.changelog import generate_changelog, get_commit_log_for_head_tag


def test_generate_changelog_contains_only_current_release_commits(tmp_path: Path):
    output = tmp_path / "changelog.md"

    generate_changelog("abc1234 fix: current release bug\ndef5678 fix: current release UI", output)

    assert (
        output.read_text(encoding="utf-8")
        == "## 本次改动\n- abc1234 fix: current release bug\n- def5678 fix: current release UI\n"
    )


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
