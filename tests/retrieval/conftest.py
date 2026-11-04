from datetime import date

import pytest
from db_fakes import FakeClock, FakeEmbedder  # shared fakes live in tests/db

from minal.db import Alignment, Course, Database, Faculty, PutRequest
from minal.db.backends.memory import MemoryBackend

TODAY = date(2026, 11, 2)


def _put(db, record):
    db.put(PutRequest.of(record))


@pytest.fixture
def backend():
    return MemoryBackend()


@pytest.fixture
def db(backend):
    db = Database(backend, FakeEmbedder(), FakeClock())
    _put(db, Course(code="CS101", title="Intro to Programming", department="CS", credits=4,
                    description="Python basics and problem solving"))
    _put(db, Course(code="CS201", title="Machine Learning", department="CS", credits=3,
                    description="neural networks and deep learning", prerequisites=["CS101"]))
    _put(db, Course(code="CH101", title="Organic Chemistry", department="CHEM", credits=4,
                    description="synthesis and spectroscopy"))
    _put(db, Course(code="FUT100", title="Quantum Computing", department="CS", credits=3,
                    description="qubits and quantum algorithms", valid_from=date(2027, 1, 1)))
    _put(db, Faculty(id="F1", name="Dr Rao", department="CS", designation="Professor"))
    _put(db, Faculty(id="F2", name="Dr Iyer", department="CHEM"))
    _put(db, Alignment(course_code="CS201", faculty_id="F1", term="2026-Fall"))
    _put(db, Alignment(course_code="CH101", faculty_id="F2", term="2026-Fall"))
    return db


@pytest.fixture
def today():
    return lambda: TODAY
