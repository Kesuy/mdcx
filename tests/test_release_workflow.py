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
    assert workflow.count("${{ steps.verify-release-tag.outputs.commit }}") == 1
    assert 'asset_name="MDCx-${RELEASE_TAG}-${{ matrix.build }}-${{ matrix.arch }}-' in workflow
    assert "${{ steps.verify-release-tag.outputs.commit }}" in workflow
    assert 'gh release upload "$RELEASE_TAG"' in workflow
    assert "svenstaro/upload-release-action" not in workflow
    assert "github.sha" not in workflow
    assert "asset_name: MDCx-$tag-" not in workflow


def test_obsolete_manual_release_workflow_is_removed():
    assert not LEGACY_WORKFLOW.exists()


def test_release_build_has_one_automatic_trigger():
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert '  push:\n    tags:\n      - "*.*"' in workflow
    assert "  workflow_dispatch:" in workflow
    assert "  release:\n    types: [published]" not in workflow


def test_release_title_uses_standard_v_prefixed_version():
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "publish-release:" in workflow
    assert 'gh release edit "$RELEASE_TAG"' in workflow
    assert '--title "v$RELEASE_TAG"' in workflow


def test_release_is_only_published_after_both_verified_assets_are_uploaded():
    workflow = WORKFLOW.read_text(encoding="utf-8")

    build_index = workflow.index("  build-app:")
    publish_index = workflow.index("  publish-release:")
    draft_index = workflow.index("gh release create", publish_index)
    upload_index = workflow.index("gh release upload", draft_index)
    verify_index = workflow.index("Verify uploaded Release assets", upload_index)
    publish_draft_index = workflow.index("--draft=false", upload_index)

    assert build_index < publish_index < draft_index < upload_index < verify_index < publish_draft_index
    assert "needs: build-app" in workflow[publish_index:]
    assert "Verify complete asset set" in workflow[publish_index:]
    assert "--draft" in workflow[draft_index:upload_index]
    assert "concurrency:" in workflow
    assert "cancel-in-progress: false" in workflow


def test_pr_ci_has_locked_windows_build_and_both_smoke_checks():
    workflow = CI_WORKFLOW.read_text(encoding="utf-8")

    windows = workflow[workflow.index("  windows-smoke:") :]
    assert "runs-on: windows-latest" in windows
    assert "uv sync --locked --all-extras --dev" in windows
    assert "pytest tests/core tests/controllers" in windows
    assert "tests/test_scrape_session.py" in windows
    assert "scripts/smoke_main_window.py" in windows
    assert "scripts/build.py --debug" in windows
    assert ".\\dist\\MDCx.exe --smoke-test" in windows


def test_linux_test_jobs_install_qt_egl_runtime_before_pytest():
    for workflow_path in (WORKFLOW, CI_WORKFLOW):
        workflow = workflow_path.read_text(encoding="utf-8")
        install_index = workflow.index("sudo apt-get install --no-install-recommends -y libegl1")
        pytest_index = workflow.index("pytest tests -q")

        assert install_index < pytest_index
