from fastapi.testclient import TestClient

from main import app
from plugins.pointer_calibration import router as pointer_router


def test_pointer_calibration_lifecycle(tmp_path, monkeypatch):
    test_data_path = tmp_path / "pointer_calibration.json"
    monkeypatch.setattr(pointer_router, "DATA_PATH", test_data_path)

    with TestClient(app) as client:
        # Initial calibration is null
        res = client.get("/api/pointer/calibration")
        assert res.status_code == 200
        assert res.json()["calibration"] is None

        # Invalid narrow calibration rejected
        bad_payload = {
            "version": 1,
            "sourceLeft": 0.5,
            "sourceRight": 0.51,  # diff < 0.05
            "sourceTop": 0.2,
            "sourceBottom": 0.8,
            "targetLeft": 0.1,
            "targetRight": 0.9,
            "targetTop": 0.14,
            "targetBottom": 0.9,
        }
        res = client.post("/api/pointer/calibration", json=bad_payload)
        assert res.status_code == 422

        # Valid calibration saved
        good_payload = {
            "version": 1,
            "sourceLeft": 0.2,
            "sourceRight": 0.8,
            "sourceTop": 0.15,
            "sourceBottom": 0.85,
            "targetLeft": 0.1,
            "targetRight": 0.9,
            "targetTop": 0.14,
            "targetBottom": 0.9,
        }
        res = client.post("/api/pointer/calibration", json=good_payload)
        assert res.status_code == 200
        assert res.json()["status"] == "saved"
        assert res.json()["calibration"]["sourceLeft"] == 0.2

        # GET returns saved calibration
        res = client.get("/api/pointer/calibration")
        assert res.status_code == 200
        assert res.json()["calibration"] == good_payload

        # DELETE clears calibration
        res = client.delete("/api/pointer/calibration")
        assert res.status_code == 200
        assert res.json()["status"] == "cleared"

        # GET is back to null
        res = client.get("/api/pointer/calibration")
        assert res.status_code == 200
        assert res.json()["calibration"] is None


def test_pointer_settings_lifecycle(tmp_path, monkeypatch):
    test_data_path = tmp_path / "pointer_calibration.json"
    monkeypatch.setattr(pointer_router, "DATA_PATH", test_data_path)

    with TestClient(app) as client:
        # Initial settings return defaults
        res = client.get("/api/pointer/settings")
        assert res.status_code == 200
        settings = res.json()["settings"]
        assert settings["cameraWidth"] == 1280
        assert settings["cameraHeight"] == 720
        assert settings["clickFinger"] == "index"

        # Save custom settings
        new_settings = {
            "cameraWidth": 1920,
            "cameraHeight": 1080,
            "detectionConfidence": 0.5,
            "presenceConfidence": 0.5,
            "trackingConfidence": 0.6,
            "verticalOffsetCm": 8.0,
            "clickFinger": "middle",
            "pinchThreshold": 0.45,
        }
        res = client.post("/api/pointer/settings", json=new_settings)
        assert res.status_code == 200
        assert res.json()["status"] == "saved"
        assert res.json()["settings"]["cameraWidth"] == 1920
        assert res.json()["settings"]["clickFinger"] == "middle"

        # Invalid resolution rejected
        bad_settings = dict(new_settings)
        bad_settings["cameraWidth"] = 800
        bad_settings["cameraHeight"] = 600
        res = client.post("/api/pointer/settings", json=bad_settings)
        assert res.status_code == 422

        # Reset settings
        res = client.delete("/api/pointer/settings")
        assert res.status_code == 200
        assert res.json()["status"] == "reset"
        assert res.json()["settings"]["cameraWidth"] == 1280
