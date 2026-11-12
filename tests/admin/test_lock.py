import pytest

pytest.importorskip("fcntl")

from minal.admin.lock import StoreBusy, store_lock  # noqa: E402


def test_second_holder_is_refused_until_released(tmp_path):
    path = tmp_path / "store.lock"
    with store_lock(path):
        with pytest.raises(StoreBusy):
            with store_lock(path):
                pass
    with store_lock(path):  # free again
        pass
