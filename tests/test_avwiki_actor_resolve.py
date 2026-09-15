from mdcx.core.translate import _replace_actor_with_avwiki


def test_avwiki_replaces_empty_actor_without_using_title_name():
    result = type("Result", (), {})()
    result.actors = []
    result.all_actors = []

    _replace_actor_with_avwiki(result, "真实演员")

    assert result.actors == ["真实演员"]
    assert result.all_actors == ["真实演员"]


def test_avwiki_replaces_unknown_placeholder():
    result = type("Result", (), {})()
    result.actors = ["未知演员"]
    result.all_actors = ["未知演员"]

    _replace_actor_with_avwiki(result, "松本梨穂")

    assert result.actors == ["松本梨穂"]
    assert result.all_actors == ["松本梨穂"]


def test_avwiki_does_not_need_title_name_fallback():
    result = type("Result", (), {})()
    result.actors = []
    result.all_actors = []

    _replace_actor_with_avwiki(result, "かすみ")

    assert result.actors == ["かすみ"]
    assert result.all_actors == ["かすみ"]
