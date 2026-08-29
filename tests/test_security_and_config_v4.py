from __future__ import annotations

import json

from mdcx.config.io import atomic_write_text
from mdcx.config.models import Config
from mdcx.config.secrets import SecretStore
from mdcx.web_async import AsyncWebClient


class _Backend:
    priority = 1


class _FakeKeyring:
    def __init__(self):
        self.values = {}

    @staticmethod
    def get_keyring():
        return _Backend()

    def set_password(self, service, name, value):
        self.values[(service, name)] = value

    def get_password(self, service, name):
        return self.values.get((service, name))

    def delete_password(self, service, name):
        self.values.pop((service, name), None)


def test_async_web_client_verifies_tls_by_default_and_accepts_custom_ca():
    secure = AsyncWebClient(timeout=1)
    custom = AsyncWebClient(timeout=1, ca_bundle="C:/certs/mdcx-ca.pem")
    insecure = AsyncWebClient(timeout=1, verify_tls=False)

    assert secure._session_kwargs["verify"] is True
    assert custom._session_kwargs["verify"] == "C:/certs/mdcx-ca.pem"
    assert insecure._session_kwargs["verify"] is False


def test_secret_store_redacts_json_and_hydrates_from_keyring(monkeypatch):
    fake = _FakeKeyring()
    store = SecretStore(paths=("api_key", "translate_config.llm_key"))
    monkeypatch.setattr(store, "_keyring", lambda: fake)
    data = {"api_key": "emby-secret", "translate_config": {"llm_key": "llm-secret"}}

    protected = store.protect(data)

    assert protected.protected is True
    assert protected.data["api_key"] == ""
    assert protected.data["translate_config"]["llm_key"] == ""
    assert protected.data["secrets_backend"] == "keyring"
    assert store.hydrate(protected.data)["api_key"] == "emby-secret"
    assert store.hydrate(protected.data)["translate_config"]["llm_key"] == "llm-secret"


def test_atomic_config_write_keeps_valid_backup(tmp_path):
    path = tmp_path / "config.json"
    atomic_write_text(path, '{"version": 4}', backup=True)

    assert json.loads(path.read_text(encoding="utf-8")) == {"version": 4}
    assert json.loads((tmp_path / "config.json.bak").read_text(encoding="utf-8")) == {"version": 4}
    assert not list(tmp_path.glob("*.tmp"))


def test_config_v4_migrates_website_single_and_defaults_to_tls_verification():
    data = {"config_version": 3, "website_single": "fc2"}
    Config.update(data)
    config = Config.model_validate(data)

    assert config.config_version == 4
    assert config.selected_site.value == "fc2"
    assert "website_single" not in config.model_dump(mode="json")
    assert config.verify_tls is True
