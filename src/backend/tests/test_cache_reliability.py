from concurrent.futures import ThreadPoolExecutor
from core import cache


def test_failed_serialization_preserves_previous_entry(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "CACHE_DIR", tmp_path)
    cache.set_cached("same", {"good": True})
    cache.set_cached("same", object())
    assert cache.get_cached("same") == {"good": True}
    cache.set_cached("same", float("nan"))
    assert cache.get_cached("same") == {"good": True}
    assert not list(tmp_path.glob("*.tmp"))


def test_concurrent_cache_readers_never_see_partial_documents(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "CACHE_DIR", tmp_path)
    cache.set_cached("same", {"value": "x" * 2000})

    def update(i):
        cache.set_cached("same", {"value": str(i) * 2000})
        assert isinstance(cache.get_cached("same")["value"], str)

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(update, range(60)))
    assert not list(tmp_path.glob("*.tmp"))
