from datetime import UTC, datetime

from api.utils.dates import parse_required_range, preset_range
from core import database


def test_preset_prev_month_boundaries():
    start, end = preset_range("prev_month", datetime(2026, 2, 9, 12, 0, tzinfo=UTC))
    assert start == "2026-01-01"
    assert end == "2026-01-31"


def test_preset_ytd_boundaries():
    start, end = preset_range("ytd", datetime(2026, 2, 9, 12, 0, tzinfo=UTC))
    assert start == "2026-01-01"
    assert end == "2026-02-09"


def test_parse_required_range_end_inclusive():
    start, end_exclusive, days = parse_required_range("2026-01-01", "2026-01-31")
    assert start == datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    assert end_exclusive == datetime(2026, 2, 1, 0, 0, tzinfo=UTC)
    assert days == 31


def test_legacy_db_schema_patch_does_not_crash(monkeypatch):
    class FakeInspector:
        def get_table_names(self):
            return ["settings", "resources", "scan_runs", "cost_snapshots"]

        def get_columns(self, table):
            if table == "settings":
                return [{"name": "id"}]
            if table == "resources":
                return [{"name": "id"}, {"name": "ocid"}, {"name": "details"}]
            return [{"name": "id"}]

    class _Conn:
        def execute(self, *_args, **_kwargs):
            return None

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    class FakeEngine:
        def begin(self):
            return _Conn()

    monkeypatch.setattr(database, "inspect", lambda _engine: FakeInspector())
    monkeypatch.setattr(database, "engine", FakeEngine())
    database._ensure_settings_schema()
    database._ensure_resource_schema()
    database._ensure_sqlite_indexes()

