"""Tests for the Doomsday Hugging Face smolagents integration (pure standard library by default)."""

import json
import unittest
from unittest.mock import patch

from integrations.smolagents.doomsday_tool import (
    DoomsdaySmolagentsClient,
    get_doomsday_worker_status,
    list_doomsday_escrows,
    smolagents_tools,
    verify_doomsday_escrow,
)


class FakeSmolagentsClient(DoomsdaySmolagentsClient):
    def _get(self, path):
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


class SmolagentsClientTests(unittest.TestCase):
    def setUp(self):
        self.client = FakeSmolagentsClient()

    def test_verify_escrow_shapes_verified_response(self):
        result = self.client.verify_escrow("doomsday-network", "bounty-guard", 5)
        self.assertTrue(result["verified"])
        self.assertEqual(result["status"], "OPEN")
        self.assertEqual(result["locked_doom"], 1500.0)
        self.assertEqual(result["evidence_level"], "onchain_utxo_and_base_erc20_verified")

    def test_verify_escrow_rejects_invalid_input_before_network(self):
        self.assertEqual(self.client.verify_escrow("", "repo", 1)["status"], "INVALID_INPUT")
        self.assertEqual(self.client.verify_escrow("owner", "", 1)["status"], "INVALID_INPUT")
        self.assertEqual(self.client.verify_escrow("owner", "repo", 0)["status"], "INVALID_INPUT")

    def test_network_error_is_not_promoted(self):
        result = self.client.verify_escrow("example", "repo", 99)
        self.assertEqual(result["status"], "ERROR")
        self.assertNotIn("verified", result)

    def test_list_escrows(self):
        result = self.client.list_open_escrows()
        self.assertEqual(result["total_locked_doom"], 1500.0)
        self.assertEqual(len(result["open_escrows"]), 1)

    def test_worker_status(self):
        result = self.client.worker_status("doom1worker")
        self.assertTrue(result["is_active"])
        self.assertEqual(self.client.worker_status("0xbad")["status"], "INVALID_INPUT")

    def test_plain_tools_use_default_client(self):
        with patch("integrations.smolagents.doomsday_tool._default_client", self.client):
            res = verify_doomsday_escrow("doomsday-network", "bounty-guard", 5)
            self.assertEqual(res["locked_doom"], 1500.0)
            self.assertEqual(list_doomsday_escrows()["total_locked_doom"], 1500.0)
            self.assertTrue(get_doomsday_worker_status("doom1worker")["is_active"])

    def test_optional_smolagents_wrappers(self):
        tools = smolagents_tools()
        try:
            from smolagents import Tool
        except ImportError:
            self.assertEqual(tools, [])
            return
        self.assertEqual(len(tools), 3)
        self.assertTrue(all(isinstance(tool, Tool) for tool in tools))
        self.assertEqual(
            {tool.name for tool in tools},
            {"verify_doomsday_escrow", "list_doomsday_escrows", "get_doomsday_worker_status"},
        )


if __name__ == "__main__":
    unittest.main()
