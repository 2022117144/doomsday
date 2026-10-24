"""Tests for the Doomsday Agno integration; no Agno or network is required."""

import json
import unittest
import urllib.error
from unittest.mock import patch

from integrations.agno.doomsday_tool import (
    DoomsdayAgnoClient,
    agno_tools,
    get_doomsday_worker_status,
    list_doomsday_escrows,
    verify_doomsday_escrow,
)


class FakeAgnoClient(DoomsdayAgnoClient):
    def __init__(self):
        super().__init__()
        self.last_path = None

    def _get(self, path):
        self.last_path = path
        if path == "/escrow/doomsday-network/bounty-guard/5":
            return {
                "issue_ref": "doomsday-network/bounty-guard#5",
                "verified_escrow": True,
                "status": "OPEN",
                "locked_doom": 1500.0,
                "evidence_level": "onchain_utxo_and_base_erc20_verified",
                "wdoom_base_contract": "0x623c84A5E04bF715018203334b0eFE41696eBC3E",
            }
        if path == "/escrow/list":
            return {
                "open_escrows": [{"issue_ref": "doomsday-network/bounty-guard#5"}],
                "total_open_bounties": 1,
                "total_locked_doom": 1500.0,
            }
        if path == "/pool/worker/doom1worker":
            return {"address": "doom1worker", "is_active": True, "round_shares": 3}
        return {"error": "HTTP 404: Not Found", "status": "ERROR"}


class AgnoClientTests(unittest.TestCase):
    def setUp(self):
        self.client = FakeAgnoClient()

    def test_verify_escrow_shapes_verified_response(self):
        result = self.client.verify_escrow("doomsday-network", "bounty-guard", 5)
        self.assertTrue(result["verified"])
        self.assertEqual(result["status"], "OPEN")
        self.assertEqual(result["locked_doom"], 1500.0)
        self.assertIn("/escrow/doomsday-network/bounty-guard/5", result["verify_url"])

    def test_verify_escrow_encodes_path_components(self):
        self.client.verify_escrow("owner/name", "repo name", 7)
        self.assertEqual(self.client.last_path, "/escrow/owner%2Fname/repo%20name/7")

    def test_verify_escrow_rejects_invalid_input_before_network(self):
        self.assertEqual(self.client.verify_escrow("", "repo", 1)["status"], "INVALID_INPUT")
        self.assertEqual(self.client.verify_escrow("owner", "repo", 0)["status"], "INVALID_INPUT")
        self.assertIsNone(self.client.last_path)

    def test_http_error_is_not_promoted_to_verified_escrow(self):
        result = self.client.verify_escrow("example", "repo", 99)
        self.assertEqual(result["status"], "ERROR")
        self.assertNotIn("verified", result)

    def test_list_open_escrows(self):
        result = self.client.list_open_escrows()
        self.assertEqual(result["total_locked_doom"], 1500.0)
        self.assertEqual(len(result["open_escrows"]), 1)

    def test_worker_status_and_invalid_address(self):
        result = self.client.worker_status("doom1worker")
        self.assertTrue(result["is_active"])
        self.assertEqual(self.client.worker_status("0xbad")["status"], "INVALID_INPUT")

    def test_plain_functions_use_default_client(self):
        with patch("integrations.agno.doomsday_tool._default_client", self.client):
            result = json.loads(json.dumps(verify_doomsday_escrow("doomsday-network", "bounty-guard", 5)))
            self.assertEqual(result["locked_doom"], 1500.0)
            self.assertEqual(list_doomsday_escrows()["total_locked_doom"], 1500.0)
            self.assertTrue(get_doomsday_worker_status("doom1worker")["is_active"])

    def test_agno_tools_are_plain_typed_callables(self):
        tools = agno_tools()
        self.assertEqual(
            {tool.__name__ for tool in tools},
            {"verify_doomsday_escrow", "list_doomsday_escrows", "get_doomsday_worker_status"},
        )
        self.assertTrue(all(callable(tool) for tool in tools))

    def test_http_client_sets_headers_and_decodes_json(self):
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return b'{"status":"OPEN"}'

        client = DoomsdayAgnoClient(base_url="https://example.test/")
        with patch("urllib.request.urlopen", return_value=FakeResponse()) as urlopen:
            result = client._get("/escrow/list")
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://example.test/escrow/list")
        self.assertEqual(request.get_header("Accept"), "application/json")
        self.assertEqual(request.get_header("User-agent"), "Doomsday-Agno/1.0")
        self.assertEqual(result["status"], "OPEN")

    def test_http_and_network_errors_are_explicit(self):
        client = DoomsdayAgnoClient()
        error = urllib.error.HTTPError("https://example.test", 503, "Unavailable", {}, None)
        with patch("urllib.request.urlopen", side_effect=error):
            self.assertEqual(client._get("/escrow/list")["status"], "ERROR")
        with patch("urllib.request.urlopen", side_effect=OSError("offline")):
            self.assertEqual(client._get("/escrow/list")["status"], "NETWORK_FAILURE")


if __name__ == "__main__":
    unittest.main()