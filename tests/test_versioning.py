import pytest
from typer.testing import CliRunner

from mdcx.versioning import compare_versions, is_newer_version, parse_version


def test_semantic_version_starts_a_newer_generation_than_legacy_date_versions():
    assert compare_versions("3.0", "220260801") > 0
    assert is_newer_version("3.0", "220260801") is True


def test_semantic_versions_compare_each_numeric_component():
    assert parse_version("3.10.2") > parse_version("3.9.12")
    assert is_newer_version("3.1", "3.0") is True
    assert is_newer_version("3.0", "3.0") is False


def test_invalid_versions_are_rejected_without_crashing_update_checks():
    assert parse_version("release-latest") is None
    assert parse_version("v3.1") is None
    assert compare_versions("release-latest", "3.0") is None
    assert is_newer_version("release-latest", "3.0") is False


def test_update_check_accepts_semantic_release_tags(monkeypatch):
    from mdcx.base import web

    class Response:
        status_code = 200
        headers = {}
        text = '{"tag_name": "3.1"}'

        @staticmethod
        def json():
            return {"tag_name": "3.1"}

    class Client:
        def __init__(self, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        @staticmethod
        def get(_url, headers):
            assert headers["User-Agent"] == "mdcx-update-check"
            return Response()

    monkeypatch.setattr(web.manager.config, "update_check", True)
    monkeypatch.setattr(web.manager.config, "use_proxy", False)
    monkeypatch.setattr(web.manager.config, "timeout", 5)
    monkeypatch.setattr(web.httpx, "Client", Client)

    assert web.check_version() == "3.1"


def test_build_and_bump_tools_support_semantic_versions(tmp_path, monkeypatch):
    from scripts import build, bump

    consts = tmp_path / "mdcx" / "consts.py"
    consts.parent.mkdir()
    consts.write_text('LOCAL_VERSION = "3.0"\n', encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert build.get_version_from_config() == "3.0"

    monkeypatch.setattr(bump, "get_consts_file", lambda: consts)
    assert bump.get_current_version() == "3.0"
    bump.update_version("3.1")
    assert consts.read_text(encoding="utf-8") == 'LOCAL_VERSION = "3.1"\n'


def test_build_and_bump_read_and_replace_unquoted_legacy_version(tmp_path, monkeypatch):
    from scripts import build, bump

    consts = tmp_path / "mdcx" / "consts.py"
    consts.parent.mkdir()
    consts.write_text("LOCAL_VERSION = 220260801\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert build.get_version_from_config() == "220260801"

    monkeypatch.setattr(bump, "get_consts_file", lambda: consts)
    assert bump.get_current_version() == "220260801"
    bump.update_version("3.0")
    assert consts.read_text(encoding="utf-8") == 'LOCAL_VERSION = "3.0"\n'


def test_build_and_bump_reject_v_prefixed_versions(tmp_path, monkeypatch):
    from scripts import build, bump

    consts = tmp_path / "consts.py"
    consts.write_text('LOCAL_VERSION = "3.0"\n', encoding="utf-8")
    monkeypatch.setattr(bump, "get_consts_file", lambda: consts)

    with pytest.raises(build.BuildError, match="版本号格式无效"):
        build.validate_build_version("v3.1")
    with pytest.raises(ValueError, match="版本号格式无效"):
        bump.update_version("v3.1")

    assert consts.read_text(encoding="utf-8") == 'LOCAL_VERSION = "3.0"\n'


@pytest.mark.parametrize("invalid_version", ["3.1-alpha", "3.1junk", "v3.1"])
def test_build_and_bump_reject_malformed_stored_versions(tmp_path, monkeypatch, invalid_version):
    from scripts import build, bump

    consts = tmp_path / "mdcx" / "consts.py"
    consts.parent.mkdir()
    consts.write_text(f'LOCAL_VERSION = "{invalid_version}"\n', encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    with pytest.raises(build.BuildError):
        build.get_version_from_config()
    monkeypatch.setattr(bump, "get_consts_file", lambda: consts)
    with pytest.raises(ValueError, match="LOCAL_VERSION"):
        bump.get_current_version()


def test_bump_dry_run_rejects_invalid_explicit_version():
    from scripts import bump

    result = CliRunner().invoke(bump.app, ["--version", "v3.1", "--dry-run"])

    assert result.exit_code == 1
    assert "版本号格式无效" in result.output
    assert "预览模式" not in result.output
