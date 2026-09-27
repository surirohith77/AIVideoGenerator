import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_system_capabilities_endpoint():
    response = client.get("/api/system/capabilities")
    assert response.status_code == 200
    data = response.json()
    assert data["cpu"] is True
    assert "estimated_performance" in data

def test_presenter_consent_enforcement():
    # Attempt creation without consent -> Should fail with 400
    res = client.post("/api/presenters", json={"name": "Test Presenter", "consent_confirmed": False})
    assert res.status_code == 400

    # Creation with consent -> Success
    res = client.post("/api/presenters", json={"name": "Rohit Presenter", "consent_confirmed": True})
    assert res.status_code == 200
    p_data = res.json()
    assert p_data["name"] == "Rohit Presenter"
    assert p_data["consent_confirmed"] is True

def test_list_and_delete_presenter():
    # Create Presenter
    res = client.post("/api/presenters", json={"name": "Temp Presenter", "consent_confirmed": True})
    assert res.status_code == 200
    pres_id = res.json()["id"]

    # List
    res_list = client.get("/api/presenters")
    assert res_list.status_code == 200
    ids = [p["id"] for p in res_list.json()]
    assert pres_id in ids

    # Delete
    del_res = client.delete(f"/api/presenters/{pres_id}")
    assert del_res.status_code == 200

def test_record_reference_endpoint():
    # Create Presenter
    res = client.post("/api/presenters", json={"name": "Reference Test Presenter", "consent_confirmed": True})
    assert res.status_code == 200
    pres_id = res.json()["id"]

    # Record FACE reference with form data & file upload
    files = {"file": ("face_video.mp4", b"fake video bytes", "video/mp4")}
    data = {"kind": "FACE"}
    rec_res = client.post(f"/api/presenters/{pres_id}/record-reference", data=data, files=files)
    assert rec_res.status_code == 200, rec_res.text
    p_updated = rec_res.json()
    assert p_updated["face_reference_asset_id"] is not None
    assert p_updated["status"] == "READY"

