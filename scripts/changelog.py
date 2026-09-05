import re
import subprocess
import sys
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text


def configure_stdio_utf8() -> None:
    """确保在 Windows CI 等场景下也能输出中文日志。"""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


configure_stdio_utf8()
console = Console(legacy_windows=False)
app = typer.Typer(help="生成 changelog", context_settings={"help_option_names": ["-h", "--help"]})

RELEASE_CATEGORIES = ("新功能", "优化", "修复")
CURATED_CATEGORY_ALIASES = {
    "新功能": "新功能",
    "优化": "优化",
    "修复": "修复",
    "安全": "修复",
    "架构": "优化",
    "界面": "优化",
    "界面与架构": "优化",
    "工程": "优化",
    "依赖与工程": "优化",
}
COMMIT_TYPE_CATEGORIES = {
    "feat": "新功能",
    "perf": "优化",
    "refactor": "优化",
    "fix": "修复",
}
LEGACY_SUBJECT_TRANSLATIONS = {
    "refresh fc2cmadb sessions and images": "修复 FC2CMADB 会话续期、演员数据与图片下载处理",
}


def run_git_command(command: list[str]) -> str:
    """运行git命令并返回输出"""
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        console.print(f"[red]执行git命令失败: {' '.join(command)}[/red]")
        console.print(f"[red]错误信息: {e.stderr}[/red]")
        raise typer.Exit(1)


def git_ref_exists(ref: str) -> bool:
    """检查给定 ref 是否存在（tag / branch / commit）。"""
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", ref],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return result.returncode == 0


def get_previous_first_parent_tag(head_tag: str, pattern: str) -> str:
    """获取当前发布 tag 在主线 first-parent 上的上一发布 tag。"""
    result = subprocess.run(
        ["git", "describe", "--tags", "--abbrev=0", "--first-parent", "--match", pattern, f"{head_tag}^"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def get_latest_tag(pattern: str) -> str | None:
    """获取当前 first-parent 历史中距离 HEAD 最近的匹配 tag。"""
    result = subprocess.run(
        ["git", "describe", "--tags", "--abbrev=0", "--first-parent", "--match", pattern, "HEAD"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def get_commit_log_for_head_tag(head_tag: str, pattern: str) -> str:
    """获取匹配 pattern 的最近历史 tag 到当前 tag 的提交日志。"""
    command = ["git", "tag", "-l", pattern, "--sort=-v:refname"]
    output = run_git_command(command)
    tags = [tag for tag in output.split("\n") if tag]

    if not tags:
        if git_ref_exists(head_tag):
            command = ["git", "log", "--pretty=format:%h %s", head_tag]
        else:
            console.print(f"[yellow]tag '{head_tag}' 不存在，回退为基于 HEAD 生成。[/yellow]")
            command = ["git", "log", "--pretty=format:%h %s", "HEAD"]
        return run_git_command(command)

    if not git_ref_exists(head_tag):
        console.print(f"[yellow]tag '{head_tag}' 不存在，回退为基于 HEAD 生成。[/yellow]")
        return get_commit_log(tags[0])

    previous_tag = get_previous_first_parent_tag(head_tag, pattern)
    if previous_tag:
        command = ["git", "log", "--pretty=format:%h %s", f"{previous_tag}..{head_tag}"]
        return run_git_command(command)

    command = ["git", "log", "--pretty=format:%h %s", head_tag]
    return run_git_command(command)


def get_commit_log(from_tag: str) -> str:
    """获取从指定tag到HEAD的提交日志"""
    command = ["git", "log", "--pretty=format:%h %s", f"{from_tag}..HEAD"]
    return run_git_command(command)


def _format_release_sections(sections: dict[str, list[str]]) -> str:
    rendered = []
    for category in RELEASE_CATEGORIES:
        notes = sections[category]
        if notes:
            rendered.append(f"## {category}\n" + "".join(f"- {note}\n" for note in notes))
    return "\n".join(rendered)


def _notes_from_commit_log(commit_lines: list[str]) -> dict[str, list[str]]:
    sections = {category: [] for category in RELEASE_CATEGORIES}
    pattern = re.compile(r"^\S+\s+(feat|perf|refactor|fix)(?:\([^)]*\))?!?:\s*(.+)$", re.IGNORECASE)
    for line in commit_lines:
        match = pattern.match(line)
        if not match:
            continue
        commit_type, subject = match.groups()
        subject = LEGACY_SUBJECT_TRANSLATIONS.get(subject.casefold(), subject)
        if not re.search(r"[\u3400-\u9fff]", subject):
            console.print(f"[red]发布说明不是中文，请维护 .github/release-notes.md 或改用中文提交信息: {subject}[/red]")
            raise typer.Exit(1)
        sections[COMMIT_TYPE_CATEGORIES[commit_type.casefold()]].append(subject)
    return sections


def _notes_from_curated_content(content: str, *, version: str = "") -> dict[str, list[str]]:
    sections = {category: [] for category in RELEASE_CATEGORIES}
    current_category = ""
    in_selected_version = not version
    selected_version_found = not version
    version_heading = re.compile(r"^##\s+(\d+\.\d+(?:\.\d+)*)$")

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        version_match = version_heading.match(line)
        if version_match:
            if in_selected_version and selected_version_found:
                break
            in_selected_version = version_match.group(1) == version
            selected_version_found = selected_version_found or in_selected_version
            current_category = ""
            continue

        if not in_selected_version:
            continue

        category_prefix = "### " if version else "## "
        if line.startswith(category_prefix):
            source_category = line[len(category_prefix) :].strip()
            current_category = CURATED_CATEGORY_ALIASES.get(source_category, "")
            if not current_category:
                console.print(f"[red]不支持的 changelog 分类: {source_category}[/red]")
                raise typer.Exit(1)
            continue
        if line.startswith("- ") and current_category:
            note = line[2:].strip()
            if not re.search(r"[\u3400-\u9fff]", note):
                console.print(f"[red]发布说明不是中文: {note}[/red]")
                raise typer.Exit(1)
            sections[current_category].append(note)

    if version and not selected_version_found:
        console.print(f"[red]changelog 中未找到版本: {version}[/red]")
        raise typer.Exit(1)
    return sections


def generate_changelog(
    commit_log: str,
    output_file: Path,
    *,
    curated_content: str | None = None,
    curated_version: str = "",
) -> None:
    """生成changelog内容并写入文件"""
    commit_lines = [line.strip() for line in commit_log.splitlines() if line.strip()]
    if not commit_lines:
        console.print("[red]本次发布没有可写入的提交记录。[/red]")
        raise typer.Exit(1)
    sections = (
        _notes_from_curated_content(curated_content, version=curated_version)
        if curated_content is not None
        else _notes_from_commit_log(commit_lines)
    )
    changelog_content = _format_release_sections(sections)
    if not changelog_content:
        console.print("[red]本次发布没有“新功能 / 优化 / 修复”分类的中文说明。[/red]")
        raise typer.Exit(1)

    try:
        output_file.write_text(changelog_content, encoding="utf-8")
        console.print(f"[green]Changelog已生成到: {output_file}[/green]")
    except Exception as e:
        console.print(f"[red]写入文件失败: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def main(
    pattern: Annotated[str, typer.Option("--pattern", "-p", help="Git tag匹配模式")] = "[0-9]*",
    output: Annotated[str, typer.Option("--output", "-o", help="输出文件路径")] = "release-changelog.md",
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="显示详细信息")] = False,
    tag: Annotated[str, typer.Option("--tag", help="当前发布 tag（用于 release 工作流）")] = "",
    curated: Annotated[str, typer.Option("--curated", help="人工维护的中文分类 changelog 路径")] = "",
) -> None:
    """
    生成changelog文件

    从最新的匹配tag到HEAD的提交记录生成changelog
    """

    # 将字符串路径转换为Path对象
    output_path = Path(output)

    if verbose:
        console.print(
            Panel(
                f"[cyan]Tag模式:[/cyan] {pattern}\n[cyan]输出文件:[/cyan] {output_path}",
                title="配置信息",
                border_style="blue",
            )
        )

    if tag:
        console.print(f"[yellow]使用发布 tag 模式: {tag}[/yellow]")
        commit_log = get_commit_log_for_head_tag(tag, pattern=pattern)
    else:
        # 获取最新的匹配tag
        console.print(f"[yellow]正在查找匹配模式 '{pattern}' 的最新tag...[/yellow]")
        latest_tag = get_latest_tag(pattern)

        if not latest_tag:
            console.print(f"[red]未找到匹配模式 '{pattern}' 的tag[/red]")
            raise typer.Exit(1)

        console.print(f"[green]找到最新tag: {latest_tag}[/green]")

        # 获取提交日志
        console.print(f"[yellow]正在获取从 {latest_tag} 到 HEAD 的提交记录...[/yellow]")
        commit_log = get_commit_log(latest_tag)

    if verbose and commit_log:
        console.print("\n[cyan]提交记录预览:[/cyan]")
        # 显示前5条记录作为预览
        commit_lines = commit_log.splitlines()
        for line in commit_lines[:5]:
            console.print(f"  {line}")
        if len(commit_lines) > 5:
            console.print(f"  ... 还有 {len(commit_lines) - 5} 条记录")
        console.print()

    # 生成changelog
    console.print(f"[yellow]正在生成changelog到 {output_path}...[/yellow]")
    curated_content = None
    if curated:
        curated_path = Path(curated)
        if not curated_path.is_file():
            console.print(f"[red]人工维护的 changelog 不存在: {curated_path}[/red]")
            raise typer.Exit(1)
        curated_content = curated_path.read_text(encoding="utf-8")
    generate_changelog(commit_log, output_path, curated_content=curated_content, curated_version=tag)

    # 显示成功信息
    success_text = Text("Changelog生成完成!", style="bold green")
    console.print(Panel(success_text, border_style="green"))


if __name__ == "__main__":
    app()
