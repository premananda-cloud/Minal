import pytest
from db_fakes import FakeClock, FakeEmbedder

from minal.db import Database
from minal.db.backends.memory import MemoryBackend


@pytest.fixture
def db():
    return Database(MemoryBackend(), FakeEmbedder(), FakeClock())


@pytest.fixture
def fresh_db():
    """A second, independent database (for restore/import tests)."""
    return Database(MemoryBackend(), FakeEmbedder(), FakeClock())
