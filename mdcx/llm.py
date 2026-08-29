from __future__ import annotations

import asyncio
import contextlib
import re
import ssl
import threading
from collections.abc import Callable
from typing import TYPE_CHECKING, Literal, Protocol
from urllib.parse import urlsplit

from aiolimiter import AsyncLimiter
from httpx import AsyncClient, Timeout

if TYPE_CHECKING:
    from openai import AsyncOpenAI


class LLMProvider(Protocol):
    async def complete(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        extra_body: object | None,
    ) -> str | None: ...


class OpenAICompatibleProvider:
    """Chat Completions adapter for OpenAI-compatible third-party APIs."""

    def __init__(self, client: AsyncOpenAI):
        self.client = client

    async def complete(self, **kwargs) -> str | None:
        chat = await self.client.chat.completions.create(
            model=kwargs["model"],
            messages=[
                {"role": "system", "content": kwargs["system_prompt"]},
                {"role": "user", "content": kwargs["user_prompt"]},
            ],
            temperature=kwargs["temperature"],
            extra_body=kwargs["extra_body"],
        )
        return chat.choices[0].message.content


class OpenAIResponsesProvider:
    """Responses API adapter for the official OpenAI endpoint."""

    def __init__(self, client: AsyncOpenAI):
        self.client = client

    async def complete(self, **kwargs) -> str | None:
        response = await self.client.responses.create(
            model=kwargs["model"],
            instructions=kwargs["system_prompt"],
            input=kwargs["user_prompt"],
            temperature=kwargs["temperature"],
            extra_body=kwargs["extra_body"],
        )
        return response.output_text


class LLMClient:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        proxy: str | None = None,
        timeout: Timeout,
        rate: tuple[float, float],
        verify_tls: bool = True,
        ca_bundle: str | None = None,
        api_mode: Literal["auto", "responses", "chat_completions"] = "auto",
    ):
        self._api_key = api_key
        self._base_url = base_url
        self._proxy = proxy
        self._timeout = timeout
        self._verify_tls = verify_tls
        self._ca_bundle = ca_bundle
        self._api_mode = api_mode
        self._client: AsyncOpenAI | None = None
        self._provider: LLMProvider | None = None
        self._client_lock = threading.Lock()
        self.limiter = AsyncLimiter(*rate)
        self._closed = False
        self._close_requested = False
        self._active_requests = 0
        self._active_lock = asyncio.Lock()
        self._lease_lock = threading.Lock()
        self._leases = 0

    @property
    def initialized(self) -> bool:
        return self._client is not None

    @property
    def client(self) -> AsyncOpenAI:
        return self._get_client()

    def _tls_verify(self) -> bool | ssl.SSLContext:
        if self._ca_bundle:
            return ssl.create_default_context(cafile=self._ca_bundle)
        return self._verify_tls

    def _get_client(self) -> AsyncOpenAI:
        if self._closed:
            raise RuntimeError("LLM 客户端已关闭")
        with self._client_lock:
            if self._client is None:
                from openai import AsyncOpenAI

                self._client = AsyncOpenAI(
                    api_key=self._api_key or "not-configured",
                    base_url=self._base_url,
                    http_client=AsyncClient(
                        proxy=self._proxy,
                        verify=self._tls_verify(),
                        timeout=self._timeout,
                        follow_redirects=True,
                    ),
                    timeout=self._timeout,
                )
            return self._client

    def _get_provider(self) -> LLMProvider:
        if self._provider is None:
            mode = self._api_mode
            if mode == "auto":
                host = (urlsplit(self._base_url).hostname or "").lower()
                mode = "responses" if host == "api.openai.com" else "chat_completions"
            client = self._get_client()
            self._provider = (
                OpenAIResponsesProvider(client) if mode == "responses" else OpenAICompatibleProvider(client)
            )
        return self._provider

    def retain(self) -> None:
        with self._lease_lock:
            if self._closed:
                raise RuntimeError("LLM 客户端已关闭")
            self._leases += 1

    async def release(self) -> None:
        with self._lease_lock:
            if self._leases > 0:
                self._leases -= 1
        if self._close_requested:
            await self._close_if_idle()

    def _lease_count(self) -> int:
        with self._lease_lock:
            return self._leases

    async def _begin_request(self) -> None:
        async with self._active_lock:
            if self._closed:
                raise RuntimeError("LLM 客户端已关闭")
            self._active_requests += 1

    async def _end_request(self) -> None:
        async with self._active_lock:
            self._active_requests = max(self._active_requests - 1, 0)

    async def _is_idle(self) -> bool:
        async with self._active_lock:
            return self._active_requests == 0 and self._lease_count() == 0

    async def _close_if_idle(self) -> bool:
        if not await self._is_idle():
            return False
        await self.close()
        return True

    async def close_when_idle(self, *, poll_interval: float = 0.2) -> None:
        self._close_requested = True
        while not await self._is_idle():
            await asyncio.sleep(poll_interval)
        await self.close()

    async def close(self) -> None:
        if self._closed:
            return
        self._close_requested = True
        self._closed = True
        client = self._client
        if client is not None:
            with contextlib.suppress(Exception):
                await client.close()

    async def ask(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.8,
        max_try: int,
        log_fn: Callable[[str], None] = lambda _: None,
        extra_body: object | None = None,
    ) -> str | None:
        wait = 1
        await self._begin_request()
        try:
            async with self.limiter:
                for _ in range(max_try):
                    try:
                        text = await self._get_provider().complete(
                            model=model,
                            system_prompt=system_prompt,
                            user_prompt=user_prompt,
                            temperature=temperature,
                            extra_body=extra_body,
                        )
                        break
                    except Exception as exc:
                        log_fn(f"⚠️ LLM API 请求失败: {exc}, {wait}s 后重试")
                        await asyncio.sleep(wait)
                        wait *= 2
                else:
                    log_fn("❌ LLM API 请求失败, 已达最大重试次数\n")
                    return None
        finally:
            await self._end_request()
        if text:
            text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
        return text
