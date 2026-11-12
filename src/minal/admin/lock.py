"""Single-owner guard for the embedded store.

Embedded Chroma should be opened by one process at a time. The CLI takes this
lock before opening the store, so two admin sessions (or an admin session and,
later, the API) cannot corrupt it. On platforms without fcntl it does nothing.
"""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


class StoreBusy(Exception):
    pass


@contextmanager
def store_lock(path: Path) -> Iterator[None]:
    try:
        import fcntl
    except ImportError:  # non-POSIX: no locking available
        yield
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = open(path, "w")  # noqa: SIM115 - held open for the lock's lifetime
    try:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise StoreBusy(f"another process is using the store (lock file: {path})") from exc
        yield
    finally:
        handle.close()
