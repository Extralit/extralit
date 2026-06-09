from unittest import mock

import extralit as ex


class TestExtralit:
    def test_default_client(self):
        with mock.patch("extralit.Extralit") as mock_client:
            mock_client.return_value.api_url = "http://localhost:6900"
            mock_client.return_value.api_key = "admin.apikey"
            mock_client.return_value.workspace = "extralit"

            client = ex.Extralit(api_url="http://localhost:6900", api_key="admin.apikey")
            assert client.api_url == "http://localhost:6900"
            assert client.api_key == "admin.apikey"

    def test_multiple_clients(self):
        local_client = ex.Extralit(api_url="http://localhost:6900", api_key="admin.apikey")
        remote_client = ex.Extralit(api_url="http://argilla.production.net", api_key="admin.apikey")

        assert local_client.api_url == "http://localhost:6900"
        assert remote_client.api_url == "http://argilla.production.net"
