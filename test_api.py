from fastapi.testclient import TestClient
from api import app

client = TestClient(app)

def test_add_and_list():
    r = client.post("/api/requests/add", params={
        "user_id": 999,
        "username": "testuser",
        "room": "TestRoom",
        "date": "2030-01-01 10:00"
    })
    assert r.status_code == 200
    data = client.get("/api/requests/999")
    assert data.status_code == 200
    lst = data.json()
    assert any(x["room"] == "TestRoom" for x in lst)

def test_cancel():
    r = client.post("/api/requests/add", params={
        "user_id": 998,
        "username": "testuser",
        "room": "CancelRoom",
        "date": "2030-02-02 12:00"
    })
    assert r.status_code == 200
    lst = client.get("/api/requests/998").json()
    req_id = lst[0]["id"]
    cancel = client.post("/api/requests/cancel", params={"user_id": 998, "request_id": req_id})
    assert cancel.status_code == 200