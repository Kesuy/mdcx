from mdcx.core.translate import _replace_actor_with_avwiki


class DummyConfig:
    actor_no_name = "未知演员"


class DummyManager:
    config = DummyConfig()


def test_avwiki_replaces_unknown_actor_without_using_title_name(monkeypatch):
    from mdcx.config import manager as manager_module

    monkeypatch.setattr(manager_module.manager, "config", DummyConfig())

    result = type("Result", (), {})()
    result.actors = []
    result.all_actors = []

    _replace_actor_with_avwiki(result, "真实演员")

    assert result.actors == ["真实演员"]
    assert result.all_actors == ["真实演员"]


def test_avwiki_replaces_unknown_placeholder():
    from mdcx.config import manager as manager_module

    monkeypatch = None
    result = type("Result", (), {})()
    result.actors = ["未知演员"]
    result.all_actors = ["未知演员"]

    _replace_actor_with_avwiki(result, "松本梨穂")

    assert result.actors == ["松本梨穂"]
    assert result.all_actors == ["松本梨穂"]
