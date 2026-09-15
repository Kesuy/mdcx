"""Resume tag/dispatch after a partial failure, without moving existing tags."""

import ast
import json
import os
import re
import subprocess
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def api(path, data=None, *, missing_ok=False):
    request = Request(
        f"https://api.github.com/repos/{os.environ['GITHUB_REPOSITORY']}/{path}",
        data=json.dumps(data).encode() if data is not None else None,
        headers={
            "Authorization": f"Bearer {os.environ['GH_TOKEN']}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=30) as response:
            body = response.read()
            return json.loads(body) if body else None
    except HTTPError as error:
        if missing_ok and error.code == 404:
            return None
        raise


def git(*args):
    return subprocess.check_output(["git", *args], text=True, encoding="utf-8").strip()


def version_at(ref):
    tree = ast.parse(git("show", f"{ref}:mdcx/consts.py"))
    values = [
        ast.literal_eval(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "LOCAL_VERSION" for target in node.targets)
    ]
    if len(values) != 1 or not isinstance(values[0], str) or not re.fullmatch(r"[0-9]+\.[0-9]+(\.[0-9]+)*", values[0]):
        raise ValueError("Invalid LOCAL_VERSION")
    return values[0]


def ensure_release(commit):
    if git("rev-parse", "HEAD") != commit:
        raise ValueError("Checkout does not match release commit")
    version = version_at(commit)
    if version == version_at(f"{commit}^1"):
        return "Version unchanged; no release needed"

    tag = api(f"git/ref/tags/{version}", missing_ok=True)
    if tag is None:
        api("git/refs", {"ref": f"refs/tags/{version}", "sha": commit})
        tag = api(f"git/ref/tags/{version}")
    target = tag["object"]
    # Also accept annotated tags, but never change their target.
    while target["type"] == "tag":
        target = api(f"git/tags/{target['sha']}")["object"]
    if target["type"] != "commit" or target["sha"] != commit:
        raise ValueError(f"Tag {version} points to a different commit; refusing to dispatch")

    release = api(f"releases/tags/{version}", missing_ok=True)
    if release is not None and not release["draft"]:
        return f"Release {version} already published"

    # Cover both historical dispatches on master and new dispatches on the tag.
    page = 1
    while True:
        runs = api(f"actions/workflows/release.yml/runs?head_sha={commit}&per_page=100&page={page}")["workflow_runs"]
        if any(run["status"] != "completed" for run in runs):
            return f"Release for {commit} is already queued or running"
        if len(runs) < 100:
            break
        page += 1
    api(
        "actions/workflows/release.yml/dispatches",
        {"ref": version, "inputs": {"tag": version, "prerelease": "false"}},
    )
    return f"Release {version} dispatched"


if __name__ == "__main__":
    print(ensure_release(os.environ["RELEASE_COMMIT"]))
