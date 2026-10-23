"""Tests for the Doomsday Google ADK integration (pure standard library by default)."""

import unittest
from unittest.mock import patch

from integrations.google_adk.doomsday_tool import (
    DoomsdayADKClient,
    get_doomsday_worker_status,
    google_adk_tools,
    list_doomsday_escrows,
    verify_doomsday_escrow,
)


class FakeADKClient(DoomsdayADKClient):
    def _get(self, path):
        if path == "/escrow/doomsday-network/doomsday/11":
            return {
                "issue_ref": "doomsday-network/doomsday#11",
                "verified_escrow": True,
                "status": "OPEN",
                "locked_doom": 3000.0,
                "evidence_level": "onchain_utxo_and_base_erc20_verified",
                "wdoom_base_contract": "0x623c84A5E04bF715018203334b0eFE41696eBC3E",
            }
        if path == "/escrow/list":
            return {
                "open_escrows": [{"issue_ref": "doomsday-network/doomsday#11"}],
                "total_open_bounties": 1,
                "total_locked_doom": 3000.0,
            }
        if path == "/pool/worker/doom1worker":
            return {"address": "doom1worker", "is_active": True, "round_shares": 4}
        return {"error": "HTTP 404: Not Found", "status": "ERROR"}


class ADKClientTests(unittest.TestCase):
    def setUp(self):
        self.client = FakeADKClient()

    def test_verify_escrow_shapes_verified_response(self):
        result = self.client.verify_escrow("doomsday-network", "doomsday", 11)
        self.assertTrue(result["verified"])
        self.assertEqual(result["status"], "OPEN")
        self.assertEqual(result["locked_doom"], 3000.0)

    def test_invalid_input_is_local(self):
        self.assertEqual(self.client.verify_escrow("", "doomsday", 11)["status"], "INVALID_INPUT")
        self.assertEqual(self.client.verify_escrow("owner", "repo", -1)["status"], "INVALID_INPUT")

    def test_network_error_is_not_promoted(self):
        result = self.client.verify_escrow("example", "repo", 99)
        self.assertEqual(result["status"], "ERROR")
        self.assertNotIn("verified", result)

    def test_list_escrows(self):
        result = self.client.list_open_escrows()
        self.assertEqual(result["total_locked_doom"], 3000.0)
        self.assertEqual(len(result["open_escrows"]), 1)

    def test_worker_status(self):
        result = self.client.worker_status("doom1worker")
        self.assertTrue(result["is_active"])
        self.assertEqual(self.client.worker_status("bad")["status"], "INVALID_INPUT")

    def test_plain_tools_use_default_client(self):
        with patch("integrations.google_adk.doomsday_tool._default_client", self.client):
            self.assertEqual(verify_doomsday_escrow("doomsday-network", "doomsday", 11)["locked_doom"], 3000.0)
            self.assertEqual(list_doomsday_escrows()["total_locked_doom"], 3000.0)
            self.assertTrue(get_doomsday_worker_status("doom1worker")["is_active"])

    def test_optional_adk_function_tools(self):
        tools = google_adk_tools()
        try:
            from google.adk.tools import FunctionTool
        except ImportError:
            self.assertEqual(tools, [])
            return
        self.assertEqual(len(tools), 3)
        self.assertTrue(all(isinstance(tool, FunctionTool) for tool in tools))
        self.assertEqual(
            {tool.name for tool in tools},
            {"verify_doomsday_escrow", "list_doomsday_escrows", "get_doomsday_worker_status"},
        )
        declaration = tools[0]._get_declaration()
        self.assertEqual(declaration.name, "verify_doomsday_escrow")


if __name__ == "__main__":
    unittest.main()
