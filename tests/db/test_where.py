from minal.db.where import matches, to_chroma


def test_equality_and_operators():
    meta = {"a": 1, "b": "x", "n": 5}
    assert matches(meta, {"a": 1})
    assert not matches(meta, {"a": 2})
    assert matches(meta, {"n": {"$gte": 5, "$lte": 9}})
    assert not matches(meta, {"n": {"$gt": 5}})
    assert matches(meta, {"b": {"$in": ["x", "y"]}})
    assert matches(meta, {"b": {"$ne": "z"}})


def test_missing_field_never_matches_except_ne():
    assert not matches({}, {"a": 1})
    assert not matches({}, {"a": {"$lte": 1}})
    assert matches({}, {"a": {"$ne": 1}})


def test_to_chroma_shapes():
    assert to_chroma(None) is None
    assert to_chroma({}) is None
    assert to_chroma({"a": 1}) == {"a": 1}
    assert to_chroma({"n": {"$gte": 1, "$lte": 2}}) == {
        "$and": [{"n": {"$gte": 1}}, {"n": {"$lte": 2}}]
    }
