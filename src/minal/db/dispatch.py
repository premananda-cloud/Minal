"""Transport-neutral command layer.

    Dispatcher(db).handle("search", {"text": "machine learning"})
    -> {"ok": True, "result": {...}}  or  {"ok": False, "error": {"code": ...}}

The CLI and a future HTTP route both call this and nothing else. A Dispatcher
built around a DatabaseReader simply has no write commands.
"""
from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ValidationError

from .contract import Empty, KeyRequest, ListRequest, PutRequest, ReindexRequest, SearchRequest
from .errors import DatabaseError, InvalidRequest, UnknownCommand

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Command:
    name: str
    request: type[BaseModel]
    method: str


COMMANDS: tuple[Command, ...] = (
    Command("get", KeyRequest, "get"),
    Command("list", ListRequest, "list_records"),
    Command("search", SearchRequest, "search"),
    Command("history", KeyRequest, "history"),
    Command("stats", Empty, "stats"),
    Command("put", PutRequest, "put"),
    Command("retire", KeyRequest, "retire"),
    Command("purge", KeyRequest, "purge"),
    Command("reindex", ReindexRequest, "reindex"),
)


def _error(code: str, message: str, details: Any = None) -> dict[str, Any]:
    return {"ok": False, "error": {"code": code, "message": message, "details": details}}


class Dispatcher:
    def __init__(self, target: Any) -> None:
        self._target = target
        self._commands = {c.name: c for c in COMMANDS if hasattr(target, c.method)}

    @property
    def commands(self) -> list[str]:
        return sorted(self._commands)

    def handle(self, command: str, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        cmd = self._commands.get(command)
        if cmd is None:
            err = UnknownCommand(f"unknown command {command!r}", details={"available": self.commands})
            return _error(err.code, err.message, err.details)
        try:
            request = cmd.request.model_validate(dict(payload or {}))
            result = getattr(self._target, cmd.method)(request)
            return {"ok": True, "result": result.model_dump(mode="json")}
        except ValidationError as exc:
            details = exc.errors(include_url=False, include_context=False, include_input=False)
            err = InvalidRequest("request failed validation", details=details)
            return _error(err.code, err.message, err.details)
        except DatabaseError as exc:
            return _error(exc.code, exc.message, exc.details)
        except Exception:  # noqa: BLE001 - boundary: never leak internals to callers
            log.exception("unexpected error handling %r", command)
            return _error("internal_error", "unexpected error; see logs")
