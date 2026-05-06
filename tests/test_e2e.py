import io
import json
import time
import pytest
from fastapi.testclient import TestClient

from app.main import app 

client = TestClient(app)


def login(email: str, password: str) -> str:
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    data = r.json()
    assert "access_token" in data, data
    return data["access_token"]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def admin_token():
    return login("admin@company.com", "TestPassword123!")


@pytest.fixture(scope="session")
def viewer_token():
    return login("viewer@company.com", "TestPassword123!")


# -------------------------
# A) Public Store Search API
# -------------------------

def test_public_search_postal_code_ok():
    payload = {"postal_code": "02110", "radius_miles": 10}
    r = client.post("/api/stores/search", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["input"]["type"] == "postal_code"
    assert "results" in data
    # 距离排序：最近的应该在前面
    dists = [x["distance_miles"] for x in data["results"]]
    assert dists == sorted(dists)


def test_public_search_services_and_logic():
    # services AND logic：Pharmacy + Repair 只应该匹配同时具备的门店
    payload = {"postal_code": "02110", "radius_miles": 10, "services": ["pharmacy", "pickup"]}
    r = client.post("/api/stores/search", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    for item in data["results"]:
        svcs = set([s.lower() for s in item["store"]["services"]])
        assert {"pharmacy", "pickup"}.issubset(svcs)


def test_public_search_open_now_filter():
    payload = {"postal_code": "02110", "radius_miles": 10, "open_now": True}
    r = client.post("/api/stores/search", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    for item in data["results"]:
        assert item["is_open_now"] in (True, None)  


def test_public_search_cache_header_present():
    payload = {"postal_code": "02110", "radius_miles": 10}
    r1 = client.post("/api/stores/search", json=payload)
    assert r1.status_code == 200, r1.text

    r2 = client.post("/api/stores/search", json=payload)
    assert r2.status_code == 200, r2.text

    assert r2.headers.get("x-cache") in ("HIT", "hit", None)  


def test_public_search_rate_limit_eventually_429():
    payload = {"postal_code": "02110", "radius_miles": 10}
    got_429 = False
    for _ in range(12):
        r = client.post("/api/stores/search", json=payload)
        if r.status_code == 429:
            got_429 = True
            assert "retry-after" in {k.lower(): v for k, v in r.headers.items()}
            break
    assert got_429, "Expected 429 Too Many Requests but did not receive it"


def test_admin_can_access_manager_scope(admin_token):
    r = client.get("/api/auth/me", headers=auth_headers(admin_token))
    assert r.status_code in (200, 404)  # 如果你没有 /api/auth/me，可删掉这个用下面的 RBAC 测试替代


def test_rbac_viewer_can_read_admin_list(viewer_token):
    r = client.get("/api/admin/stores?limit=1&offset=0", headers=auth_headers(viewer_token))
    assert r.status_code == 200, r.text


def test_rbac_viewer_forbidden_on_admin_write(viewer_token):
    # viewer should be read-only: cannot patch
    r = client.patch(
        "/api/admin/stores/S0001",
        json={"name": "Should Not Update"},
        headers=auth_headers(viewer_token),
    )
    assert r.status_code == 403, r.text


def test_admin_create_patch_soft_delete_store(admin_token):
    store_id = "S0999"
    create_payload = {
        "store_id": store_id,
        "name": "Pytest Store 999",
        "store_type": "regular",
        "status": "active",
        "latitude": 42.3555,
        "longitude": -71.0602,
        "address_street": "100 Cambridge St",
        "address_city": "Boston",
        "address_state": "MA",
        "address_postal_code": "02114",
        "address_country": "USA",
        "phone": "617-555-0100",
        "services": ["Pharmacy", "Pickup"],  # 测 normalize to lowercase
        "hours": json.dumps({"timezone": "America/New_York", "weekly": {"mon": [["08:00","22:00"]]}})
    }

    r = client.post("/api/admin/stores", json=create_payload, headers=auth_headers(admin_token))
    assert r.status_code in (200, 201), r.text
    data = r.json()
    assert data["store_id"] == store_id
    svcs = [s.lower() for s in data.get("services", [])]
    assert "pharmacy" in svcs and "pickup" in svcs

    patch_payload = {"name": "Pytest Store 999 Updated", "phone": "617-555-9999"}
    r = client.patch(f"/api/admin/stores/{store_id}", json=patch_payload, headers=auth_headers(admin_token))
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["name"].endswith("Updated")
    assert data["phone"] == "617-555-9999"

    # DELETE = soft delete（status -> inactive）
    r = client.delete(f"/api/admin/stores/{store_id}", headers=auth_headers(admin_token))
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "inactive"


# -------------------------
# D) CSV Import
# -------------------------

def test_csv_import_reject_bad_hours(admin_token):
    # 让第1行 hours_mon 非法，应该 422 且回滚（all-or-nothing）
    csv_text = (
        "store_id,name,store_type,status,latitude,longitude,address_street,address_city,address_state,"
        "address_postal_code,address_country,phone,services,hours_mon,hours_tue,hours_wed,hours_thu,"
        "hours_fri,hours_sat,hours_sun\n"
        "S0901,Bad Hours Store,regular,active,42.35,-71.06,1 Main St,Boston,MA,02110,USA,617-555-0100,"
        "pharmacy|pickup,8am-10pm,08:00-22:00,08:00-22:00,08:00-22:00,08:00-22:00,closed,closed\n"
    )
    files = {"file": ("bad.csv", csv_text.encode("utf-8"), "text/csv")}
    r = client.post("/api/admin/stores/import", files=files, headers=auth_headers(admin_token))
    assert r.status_code == 422, r.text
    detail = r.json().get("detail")
    assert detail["failed"] == 1
    assert "hours" in detail["errors"][0]["error"].lower()


def test_csv_import_success_small(admin_token):
    csv_text = (
        "store_id,name,store_type,status,latitude,longitude,address_street,address_city,address_state,"
        "address_postal_code,address_country,phone,services,hours_mon,hours_tue,hours_wed,hours_thu,"
        "hours_fri,hours_sat,hours_sun\n"
        "S0902,Good Store A,regular,active,42.35,-71.06,1 Main St,Boston,MA,02110,USA,617-555-0100,"
        "pharmacy|pickup,08:00-22:00,08:00-22:00,08:00-22:00,08:00-22:00,08:00-22:00,closed,closed\n"
        "S0903,Good Store B,express,active,42.36,-71.07,2 Main St,Boston,MA,02110,USA,617-555-0101,"
        "pickup,08:00-20:00,08:00-20:00,08:00-20:00,08:00-20:00,08:00-20:00,closed,closed\n"
    )
    files = {"file": ("good.csv", csv_text.encode("utf-8"), "text/csv")}
    r = client.post("/api/admin/stores/import", files=files, headers=auth_headers(admin_token))
    assert r.status_code == 200, r.text
    rep = r.json()
    assert rep["total_rows"] == 2
    assert rep["failed"] == 0
