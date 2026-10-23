"""Tests for the Doomsday Haystack integration."""

import unittest
from unittest.mock import patch

from integrations.haystack.doomsday_tool import (
    DoomsdayHaystackClient,
    get_doomsday_worker_status,
    haystack_tools,
    list_doomsday_escrows,
    verify_doomsday_escrow,
)


class FakeClient(DoomsdayHaystackClient):
    def _get(self, path):
        if path == "/escrow/doomsday-network/doomsday/11":
            return {
                "issue_ref": "doomsday-network/doomsday#11",
                "verified_escrow": True,
                "status": "OPEN",
                "locked_doom": 3000.0,
                "evidence_level": "onchain_utxo_and_base_erc20_verified",
            }
        if path == "/escrow/list":
            return {"open_escrows": [{"issue_ref": "doomsday-network/doomsday#11"}], "total_locked_doom": 3000.0}
        if path == "/pool/worker/doom1worker":
            return {"address": "doom1worker", "is_active": True, "round_shares": 8}
        return {"error": "HTTP 404: Not Found", "status": "ERROR"}


class HaystackTests(unittest.TestCase):
    def setUp(self):
        self.client = FakeClient()

    def test_verify_shapes_verified_response(self):
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

    def test_plain_tools(self):
        with patch("integrations.haystack.doomsday_tool._default_client", self.client):
            self.assertEqual(verify_doomsday_escrow("doomsday-network", "doomsday", 11)["locked_doom"], 3000.0)
            self.assertEqual(list_doomsday_escrows()["total_locked_doom"], 3000.0)
            self.assertTrue(get_doomsday_worker_status("doom1worker")["is_active"])

    def test_optional_haystack_tools(self):
        tools = haystack_tools()
        try:
            from haystack.tools import Tool
        except ImportError:
            self.assertEqual(tools, [])
            return
        self.assertEqual(len(tools), 3)
        self.assertTrue(all(isinstance(t, Tool) for t in tools))
        self.assertEqual({t.name for t in tools}, {"verify_doomsday_escrow", "list_doomsday_escrows", "get_doomsday_worker_status"})
        self.assertIn("issue_number", tools[0].parameters["required"])


if __name__ == "__main__":
    unittest.main()
