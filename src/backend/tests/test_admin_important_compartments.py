from fastapi.testclient import TestClient

from main import app
from api.routes import admin


client = TestClient(app)


class _Comp:
    def __init__(self, cid, name, parent_id=None):
        self.id = cid
        self.name = name
        self.parent_id = parent_id


class _Setting:
    id = 1

    def __init__(self):
        self.important_compartments = []
        self.important_compartment_ids = []
        self.important_include_children = True


class _Query:
    def __init__(self, rows):
        self.rows = rows

    def filter(self, *_args, **_kwargs):
        return self

    def one(self):
        return self.rows[0]

    def all(self):
        return self.rows


class _FakeDB:
    def __init__(self):
        self.setting = _Setting()
        self.compartments = [
            _Comp("c-foo", "foo"),
            _Comp("c-ad1", "ad1"),
            _Comp("c-other", "other"),
        ]

    def query(self, model):
        name = getattr(model, "__name__", "")
        if name == "Setting":
            return _Query([self.setting])
        if name == "Compartment":
            return _Query(self.compartments)
        return _Query([])

    def commit(self):
        return None


def _override_admin():
    return {"sub": "tester"}


def test_get_important_compartments_schema_and_defaults():
    fake_db = _FakeDB()
    app.dependency_overrides[admin.get_db] = lambda: fake_db
    app.dependency_overrides[admin._require_admin] = _override_admin
    try:
        response = client.get("/api/v1/admin/settings/important-compartments")
        assert response.status_code == 200
        payload = response.json()
        assert set(payload.keys()) == {"success", "data"}
        assert set(payload["data"].keys()) == {"important_compartments", "include_children"}
        assert sorted(payload["data"]["important_compartments"]) == ["c-ad1", "c-foo"]
        assert payload["data"]["include_children"] is True
    finally:
        app.dependency_overrides.pop(admin.get_db, None)
        app.dependency_overrides.pop(admin._require_admin, None)


def test_post_important_compartments_persists_and_get_returns_updated():
    fake_db = _FakeDB()
    app.dependency_overrides[admin.get_db] = lambda: fake_db
    app.dependency_overrides[admin._require_admin] = _override_admin
    try:
        payload = {
            "important_compartments": ["c-other"],
            "include_children": False,
        }
        post_res = client.post("/api/v1/admin/settings/important-compartments", json=payload)
        assert post_res.status_code == 200
        post_data = post_res.json()["data"]
        assert post_data["important_compartments"] == ["c-other"]
        assert post_data["include_children"] is False

        get_res = client.get("/api/v1/admin/settings/important-compartments")
        assert get_res.status_code == 200
        get_data = get_res.json()["data"]
        assert get_data["important_compartments"] == ["c-other"]
        assert get_data["include_children"] is False
    finally:
        app.dependency_overrides.pop(admin.get_db, None)
        app.dependency_overrides.pop(admin._require_admin, None)

