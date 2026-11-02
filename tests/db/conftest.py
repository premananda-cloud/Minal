import pytest
from db_fakes import FakeClock, FakeEmbedder
from uuid import uuid4

from minal.db import Database
from minal.db.backends.memory import MemoryBackend


@pytest.fixture(params=["memory", "chroma"])
def backend(request):
    if request.param == "memory":
        return MemoryBackend()
    chromadb = pytest.importorskip("chromadb")
    from minal.db.backends.chroma import ChromaBackend

    # EphemeralClient state is shared in-process, so isolate each test by prefix.
    return ChromaBackend(chromadb.EphemeralClient(), prefix=f"t{uuid4().hex[:12]}_")


@pytest.fixture
def embedder():
    return FakeEmbedder()


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def db(backend, embedder, clock):
    return Database(backend, embedder, clock)
