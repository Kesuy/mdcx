from __future__ import annotations

import copy
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

SECRET_PATHS = (
    "translate_config.baidu_key",
    "translate_config.deepl_key",
    "translate_config.llm_key",
    "api_key",
    "theporndb_api_token",
    "javdb",
    "fc2ppvdb",
    "javbus",
)


def _get_path(data: dict[str, Any], path: str) -> str:
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, dict):
            return ""
        current = current.get(part)
    return current if isinstance(current, str) else ""


def _set_path(data: dict[str, Any], path: str, value: str) -> None:
    parts = path.split(".")
    current = data
    for part in parts[:-1]:
        child = current.get(part)
        if not isinstance(child, dict):
            child = {}
            current[part] = child
        current = child
    current[parts[-1]] = value


@dataclass
class SecretStorageResult:
    data: dict[str, Any]
    protected: bool


class SecretStore:
    """Store credentials in the operating-system credential backend.

    Missing or locked keyrings keep the legacy JSON representation so portable
    installations do not silently lose credentials.
    """

    service_name = "MDCx"

    def __init__(self, *, paths: Iterable[str] = SECRET_PATHS):
        self.paths = tuple(paths)

    @staticmethod
    def _keyring():
        import keyring

        return keyring

    def available(self) -> bool:
        try:
            backend = self._keyring().get_keyring()
            return float(getattr(backend, "priority", 0)) > 0
        except Exception:
            return False

    def protect(self, data: dict[str, Any]) -> SecretStorageResult:
        if not self.available():
            return SecretStorageResult(data=data, protected=False)

        keyring = self._keyring()
        values = {path: _get_path(data, path) for path in self.paths}
        try:
            for path, value in values.items():
                if value:
                    keyring.set_password(self.service_name, path, value)
                else:
                    try:
                        keyring.delete_password(self.service_name, path)
                    except Exception:
                        pass
        except Exception:
            return SecretStorageResult(data=data, protected=False)

        protected = copy.deepcopy(data)
        for path in self.paths:
            _set_path(protected, path, "")
        protected["secrets_backend"] = "keyring"
        return SecretStorageResult(data=protected, protected=True)

    def hydrate(self, data: dict[str, Any]) -> dict[str, Any]:
        if data.get("secrets_backend") != "keyring" or not self.available():
            return data

        keyring = self._keyring()
        hydrated = copy.deepcopy(data)
        for path in self.paths:
            try:
                value = keyring.get_password(self.service_name, path)
            except Exception:
                value = None
            if value is not None:
                _set_path(hydrated, path, value)
        return hydrated


secret_store = SecretStore()
