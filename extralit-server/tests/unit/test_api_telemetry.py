from pytest_mock import MockerFixture
from starlette.testclient import TestClient

from extralit_server._app import create_server_app
from extralit_server.settings import settings
from extralit_server.telemetry import TelemetryClient


class TestAPITelemetry:
    def test_track_api_request_call(self, test_telemetry: TelemetryClient):
        settings.enable_telemetry = True  # Forcing telemetry to be enabled for this test

        client = TestClient(create_server_app())

        client.get("/api/v1/version")

        test_telemetry.track_api_request.assert_called_once()

    def test_track_api_request_call_on_error(self, test_telemetry: TelemetryClient):
        settings.enable_telemetry = True

        client = TestClient(create_server_app())

        response = client.post("/api/v1/datasets")
        assert response.status_code == 401

        test_telemetry.track_api_request.assert_called_once()

    def test_track_api_request_with_unexpected_telemetry_error(
        self, test_telemetry: TelemetryClient, mocker: "MockerFixture"
    ):
        with mocker.patch.object(test_telemetry, "track_api_request", side_effect=Exception("mocked error")):
            settings.enable_telemetry = True

            client = TestClient(create_server_app())

            response = client.get("/api/v1/version")

            test_telemetry.track_api_request.assert_called_once()
            assert response.status_code == 200

    def test_not_track_api_request_call_when_disabled_telemetry(self, test_telemetry: TelemetryClient):
        settings.enable_telemetry = False

        client = TestClient(create_server_app())

        client.get("/api/v1/version")

        test_telemetry.track_api_request.assert_not_called()
