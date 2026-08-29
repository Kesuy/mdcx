from pathlib import Path

WORKFLOW = Path(__file__).parents[1] / ".github" / "workflows" / "release.yml"
CI_WORKFLOW = WORKFLOW.with_name("ci.yaml")
LEGACY_WORKFLOW = WORKFLOW.with_name("release.v1.yml")


def test_release_assets_use_verified_tag_identity():
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "id: verify-release-tag" in workflow
    assert 'git rev-parse --verify "refs/tags/$tag^{commit}"' in workflow
    assert 'head_commit="$(git rev-parse HEAD)"' in workflow
    assert 'if [ "$head_commit" != "$tag_commit" ]; then' in workflow
    assert 'echo "commit=$tag_commit" >> "$GITHUB_OUTPUT"' in workflow
    assert workflow.count("${{ steps.verify-release-tag.outputs.commit }}") == 2
    assert "github.sha" not in workflow
    assert "asset_name: MDCx-$tag-" not in workflow
    assert "tag: ${{ env.RELEASE_TAG }}" in workflow


def test_obsolete_manual_release_workflow_is_removed():
    assert not LEGACY_WORKFLOW.exists()


def test_release_build_has_one_automatic_trigger():
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "  release:\n    types: [published]" in workflow
    assert "  workflow_dispatch:" in workflow
    assert "  push:" not in workflow


def test_release_title_uses_standard_v_prefixed_version():
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "normalize-release-title:" in workflow
    assert 'gh release edit "$RELEASE_TAG"' in workflow
    assert '--title "v$RELEASE_TAG"' in workflow


def test_linux_test_jobs_install_qt_egl_runtime_before_pytest():
    for workflow_path in (WORKFLOW, CI_WORKFLOW):
        workflow = workflow_path.read_text(encoding="utf-8")
        install_index = workflow.index("sudo apt-get install --no-install-recommends -y libegl1")
        pytest_index = workflow.index("pytest tests -q")

        assert install_index < pytest_index
