"""LiteLLM gateway client: OpenAI-compatible /chat/completions over httpx.

Uses httpx (already a dependency) rather than an SDK so every failure maps to one of our
stable errors and tests can inject httpx.MockTransport with no network. No retries yet."""
from __future__ import annotations

from typing import Any, Self

import httpx

from minal.llm.errors import (
    LLMAuthFailed,
    LLMBadRequest,
    LLMBadResponse,
    LLMTimeout,
    LLMUnavailable,
)
from minal.llm.models import CompletionRequest, CompletionResult, LLMConfig, Usage

_SNIPPET = 500


def _error_info(resp: httpx.Response) -> tuple[str, str | None]:
    """(message, type) from an OpenAI/LiteLLM style error body; falls back to raw text."""
    try:
        err = resp.json()["error"]
        return str(err.get("message", "")), err.get("type")
    except (ValueError, KeyError, TypeError, AttributeError):
        return resp.text[:_SNIPPET], None


class LiteLLMClient:
    def __init__(
        self, config: LLMConfig | None = None, *, transport: httpx.BaseTransport | None = None
    ) -> None:
        self._config = config or LLMConfig()
        headers = {"Content-Type": "application/json"}
        if self._config.api_key is not None:
            headers["Authorization"] = f"Bearer {self._config.api_key.get_secret_value()}"
        self._http = httpx.Client(
            base_url=self._config.base_url.rstrip("/"),
            headers=headers,
            timeout=self._config.timeout_s,
            transport=transport,
        )

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        self._http.close()

    def complete(self, req: CompletionRequest) -> CompletionResult:
        payload: dict[str, Any] = {
            "model": self._config.model,
            "messages": [m.model_dump() for m in req.messages],
            "temperature": req.temperature,
            "max_tokens": req.max_tokens,
            "stream": False,
        }
        if req.stop:
            payload["stop"] = req.stop
        try:
            resp = self._http.post("/chat/completions", json=payload)
        except httpx.TimeoutException as e:
            raise LLMTimeout(
                f"LLM gateway did not answer within {self._config.timeout_s:g}s"
            ) from e
        except httpx.HTTPError as e:
            raise LLMUnavailable(
                f"Cannot reach LLM gateway at {self._config.base_url}: {e}"
            ) from e
        self._raise_for_status(resp)
        return self._parse(resp)

    @staticmethod
    def _raise_for_status(resp: httpx.Response) -> None:
        if resp.status_code < 400:
            return
        message, kind = _error_info(resp)
        details = {"status": resp.status_code, "type": kind, "message": message}
        status = resp.status_code
        # Without a database the gateway answers an unknown key with 400 "no_db_connection".
        if status in (401, 403) or kind == "no_db_connection":
            raise LLMAuthFailed("LLM gateway rejected the API key", details=details)
        if status == 429 or status >= 500:
            raise LLMUnavailable(f"LLM gateway error {status}: {message}", details=details)
        raise LLMBadRequest(f"LLM gateway rejected the request ({status}): {message}",
                            details=details)

    @staticmethod
    def _parse(resp: httpx.Response) -> CompletionResult:
        try:
            body = resp.json()
            choice = body["choices"][0]
            text = choice["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as e:
            raise LLMBadResponse(
                "LLM gateway returned an unexpected response", details=resp.text[:_SNIPPET]
            ) from e
        if not isinstance(text, str):
            raise LLMBadResponse("LLM response has no text content", details=resp.text[:_SNIPPET])
        usage = body.get("usage") or {}
        return CompletionResult(
            text=text,
            model=str(body.get("model", "")),
            finish_reason=choice.get("finish_reason"),
            usage=Usage(
                prompt_tokens=int(usage.get("prompt_tokens", 0)),
                completion_tokens=int(usage.get("completion_tokens", 0)),
                total_tokens=int(usage.get("total_tokens", 0)),
            ),
        )
