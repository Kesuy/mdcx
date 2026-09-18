import base64
from urllib.parse import parse_qs, urlparse

import pytest

from mdcx.config.manager import manager
from mdcx.tools import emby_actor_image


@pytest.mark.asyncio
async def test_upload_actor_photo_uses_base64_body_for_emby(monkeypatch: pytest.MonkeyPatch, tmp_path):
    captured: dict = {}
    pic_path = tmp_path / "actor.jpg"
    pic_bytes = b"\xff\xd8\xfftest-bytes"
    pic_path.write_bytes(pic_bytes)

    async def fake_post_content(url: str, *, data=None, headers=None, use_proxy=True, **kwargs):
        captured["url"] = url
        captured["data"] = data
        captured["headers"] = headers
        captured["use_proxy"] = use_proxy
        return b"", ""

    monkeypatch.setattr(manager.config, "server_type", "emby")
    monkeypatch.setattr(manager.computed.async_client, "post_content", fake_post_content)
    monkeypatch.setattr(emby_actor_image.signal, "show_log_text", lambda text: None)

    result, error = await emby_actor_image._upload_actor_photo(
        "http://127.0.0.1:8096/emby/Items/1/Images/Primary?api_key=test-token", pic_path
    )

    assert result is True
    assert error == ""
    assert captured["data"] == base64.b64encode(pic_bytes)
    assert captured["headers"] == {"Content-Type": "image/jpeg"}
    assert captured["use_proxy"] is False


@pytest.mark.asyncio
async def test_get_emby_actor_list_uses_jellyfin_actor_endpoint(monkeypatch: pytest.MonkeyPatch):
    captured: dict = {}

    async def fake_get_json(url: str, *, headers=None, use_proxy=True, **kwargs):
        captured["url"] = url
        captured["headers"] = headers
        captured["use_proxy"] = use_proxy
        return {"Items": [{"Name": "演员A"}]}, ""

    monkeypatch.setattr(manager.config, "server_type", "jellyfin")
    monkeypatch.setattr(manager.config, "emby_url", "http://127.0.0.1:8096")
    monkeypatch.setattr(manager.config, "api_key", "secret-token")
    monkeypatch.setattr(manager.config, "user_id", "user-1")
    monkeypatch.setattr(manager.computed.async_client, "get_json", fake_get_json)
    monkeypatch.setattr(emby_actor_image.signal, "show_log_text", lambda text: None)

    actor_list = await emby_actor_image._get_emby_actor_list()

    parsed = urlparse(captured["url"])
    query = parse_qs(parsed.query)

    assert actor_list == [{"Name": "演员A"}]
    assert parsed.scheme == "http"
    assert parsed.netloc == "127.0.0.1:8096"
    assert parsed.path == "/Persons"
    assert query["personTypes"] == ["Actor"]
    assert query["fields"] == [",".join(emby_actor_image.JELLYFIN_PERSON_FIELDS)]
    assert query["enableImages"] == ["true"]
    assert query["userId"] == ["user-1"]
    assert "api_key" not in query
    assert "ApiKey" not in query
    assert captured["headers"] == {"Authorization": 'MediaBrowser Token="secret-token"'}
    assert captured["use_proxy"] is False


@pytest.mark.asyncio
async def test_upload_actor_photo_uses_base64_body_for_jellyfin(monkeypatch: pytest.MonkeyPatch, tmp_path):
    captured: dict = {}
    pic_path = tmp_path / "actor.jpg"
    pic_bytes = b"\xff\xd8\xfftest-bytes"
    pic_path.write_bytes(pic_bytes)

    async def fake_post_content(url: str, *, data=None, headers=None, use_proxy=True, **kwargs):
        captured["url"] = url
        captured["data"] = data
        captured["headers"] = headers
        captured["use_proxy"] = use_proxy
        return b"", ""

    monkeypatch.setattr(manager.config, "server_type", "jellyfin")
    monkeypatch.setattr(manager.config, "api_key", "secret-token")
    monkeypatch.setattr(manager.computed.async_client, "post_content", fake_post_content)
    monkeypatch.setattr(emby_actor_image.signal, "show_log_text", lambda text: None)

    result, error = await emby_actor_image._upload_actor_photo("http://127.0.0.1:8096/Items/1/Images/Primary", pic_path)

    assert result is True
    assert error == ""
    assert captured["data"] == base64.b64encode(pic_bytes)
    assert captured["headers"] == {
        "Content-Type": "image/jpeg",
        "Authorization": 'MediaBrowser Token="secret-token"',
    }
    assert captured["use_proxy"] is False


@pytest.mark.asyncio
async def test_get_actor_detail_reuses_jellyfin_list_payload(monkeypatch: pytest.MonkeyPatch):
    actor = {
        "Name": "演员A",
        "Id": "1",
        "ServerId": "server-1",
        "Overview": "",
        "ProviderIds": {},
        "ProductionLocations": [],
        "Taglines": [],
        "Genres": [],
        "Tags": [],
    }

    async def fake_get_json(*args, **kwargs):
        raise AssertionError("Jellyfin 演员详情不应再次请求 /Persons/{name}")

    monkeypatch.setattr(manager.config, "server_type", "jellyfin")
    monkeypatch.setattr(manager.computed.async_client, "get_json", fake_get_json)

    result, error = await emby_actor_image._get_actor_detail(actor)

    assert result is actor
    assert error == ""


def test_generate_server_url_uses_new_jellyfin_endpoints(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(manager.config, "server_type", "jellyfin")
    monkeypatch.setattr(manager.config, "emby_url", "http://127.0.0.1:8096/")
    monkeypatch.setattr(manager.config, "api_key", "legacy-key-should-not-appear")
    monkeypatch.setattr(manager.config, "user_id", "user-1")

    homepage, actor_person, pic_url, backdrop_url, backdrop_url_0, update_url = emby_actor_image._generate_server_url(
        {"Name": "梦乃 爱华", "Id": "item-1", "ServerId": "server-1"}
    )

    assert homepage == "http://127.0.0.1:8096/web/index.html#!/details?id=item-1&serverId=server-1"
    assert actor_person.startswith("http://127.0.0.1:8096/Persons/")
    assert "%E6%A2%A6%E4%B9%83%20%E7%88%B1%E5%8D%8E" in actor_person
    assert actor_person.endswith("?userId=user-1")
    assert pic_url == "http://127.0.0.1:8096/Items/item-1/Images/Primary"
    assert backdrop_url == "http://127.0.0.1:8096/Items/item-1/Images/Backdrop"
    assert backdrop_url_0 == "http://127.0.0.1:8096/Items/item-1/Images/Backdrop/0"
    assert update_url == "http://127.0.0.1:8096/Items/item-1"
    assert "api_key" not in actor_person
    assert "api_key" not in pic_url
    assert "api_key" not in backdrop_url
    assert "api_key" not in backdrop_url_0
    assert "api_key" not in update_url

@pytest.mark.asyncio
async def test_get_emby_actor_list_filters_multiple_emby_libraries(monkeypatch: pytest.MonkeyPatch):
    calls: list[str] = []

    async def fake_get_json(url: str, *, headers=None, use_proxy=True, **kwargs):
        calls.append(url)
        query = parse_qs(urlparse(url).query)
        library_id = query["ParentId"][0]
        if library_id == "139975":
            return {"Items": [{"Id": "actor-1", "Name": "演员A"}, {"Id": "actor-2", "Name": "演员B"}]}, ""
        return {"Items": [{"Id": "actor-2", "Name": "演员B"}, {"Id": "actor-3", "Name": "演员C"}]}, ""

    monkeypatch.setattr(manager.config, "server_type", "emby")
    monkeypatch.setattr(manager.config, "emby_url", "http://127.0.0.1:8096")
    monkeypatch.setattr(manager.config, "api_key", "secret-token")
    monkeypatch.setattr(manager.config, "user_id", "user-1")
    monkeypatch.setattr(manager.config, "actor_photo_library_scope", "selected")
    monkeypatch.setattr(manager.config, "actor_photo_library_ids", ["139975", "246810"])
    monkeypatch.setattr(manager.computed.async_client, "get_json", fake_get_json)
    monkeypatch.setattr(emby_actor_image.signal, "show_log_text", lambda text: None)

    actor_list = await emby_actor_image._get_emby_actor_list()

    assert [actor["Id"] for actor in actor_list] == ["actor-1", "actor-2", "actor-3"]
    assert len(calls) == 2
    for expected_id, url in zip(("139975", "246810"), calls, strict=True):
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        assert parsed.path == "/emby/Persons"
        assert query["ParentId"] == [expected_id]
        assert query["api_key"] == ["secret-token"]
        assert query["userid"] == ["user-1"]


@pytest.mark.asyncio
async def test_get_emby_actor_list_filters_multiple_jellyfin_libraries(monkeypatch: pytest.MonkeyPatch):
    calls: list[tuple[str, dict | None]] = []

    async def fake_get_json(url: str, *, headers=None, use_proxy=True, **kwargs):
        calls.append((url, headers))
        query = parse_qs(urlparse(url).query)
        library_id = query["parentId"][0]
        if library_id == "lib-a":
            return {"Items": [{"Id": "actor-1", "Name": "演员A"}, {"Id": "actor-2", "Name": "演员B"}]}, ""
        return {"Items": [{"Id": "actor-2", "Name": "演员B"}, {"Id": "actor-3", "Name": "演员C"}]}, ""

    monkeypatch.setattr(manager.config, "server_type", "jellyfin")
    monkeypatch.setattr(manager.config, "emby_url", "http://127.0.0.1:8096")
    monkeypatch.setattr(manager.config, "api_key", "secret-token")
    monkeypatch.setattr(manager.config, "user_id", "user-1")
    monkeypatch.setattr(manager.config, "actor_photo_library_scope", "selected")
    monkeypatch.setattr(manager.config, "actor_photo_library_ids", ["lib-a", "lib-b"])
    monkeypatch.setattr(manager.computed.async_client, "get_json", fake_get_json)
    monkeypatch.setattr(emby_actor_image.signal, "show_log_text", lambda text: None)

    actor_list = await emby_actor_image._get_emby_actor_list()

    assert [actor["Id"] for actor in actor_list] == ["actor-1", "actor-2", "actor-3"]
    assert len(calls) == 2
    for expected_id, (url, headers) in zip(("lib-a", "lib-b"), calls, strict=True):
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        assert parsed.path == "/Persons"
        assert query["parentId"] == [expected_id]
        assert query["personTypes"] == ["Actor"]
        assert query["userId"] == ["user-1"]
        assert headers == {"Authorization": 'MediaBrowser Token="secret-token"'}


@pytest.mark.asyncio
async def test_get_emby_actor_list_stops_when_selected_library_ids_are_empty(monkeypatch: pytest.MonkeyPatch):
    async def fake_get_json(*args, **kwargs):
        raise AssertionError("未填写指定媒体库 ID 时不应请求服务器")

    monkeypatch.setattr(manager.config, "server_type", "emby")
    monkeypatch.setattr(manager.config, "api_key", "secret-token")
    monkeypatch.setattr(manager.config, "actor_photo_library_scope", "selected")
    monkeypatch.setattr(manager.config, "actor_photo_library_ids", [])
    monkeypatch.setattr(manager.computed.async_client, "get_json", fake_get_json)
    monkeypatch.setattr(emby_actor_image.signal, "show_log_text", lambda text: None)

    assert await emby_actor_image._get_emby_actor_list() == []

