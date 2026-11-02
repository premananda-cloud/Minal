import pytest

chromadb = pytest.importorskip("chromadb")

from db_fakes import FakeEmbedder  # noqa: E402

from minal.db import Course, Database, EmbeddingModelMismatch, KeyRequest, Kind, PutRequest  # noqa: E402
from minal.db.backends.chroma import ChromaBackend  # noqa: E402


def test_data_and_model_survive_reopening(tmp_path):
    path = str(tmp_path / "chroma")
    db = Database(ChromaBackend(chromadb.PersistentClient(path=path)), FakeEmbedder())
    db.put(PutRequest.of(Course(code="CS101", title="Intro", department="CS", credits=4)))

    # A brand-new backend object has no in-process caches: everything is read from disk.
    reopened = Database(ChromaBackend(chromadb.PersistentClient(path=path)), FakeEmbedder())
    assert reopened.get(KeyRequest(kind=Kind.COURSE, key="CS101")).record["title"] == "Intro"

    wrong = Database(ChromaBackend(chromadb.PersistentClient(path=path)), FakeEmbedder("other"))
    with pytest.raises(EmbeddingModelMismatch):
        wrong.put(PutRequest.of(Course(code="CS102", title="X", department="CS", credits=1)))
