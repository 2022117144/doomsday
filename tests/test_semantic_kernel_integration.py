"""Tests for the Doomsday Semantic Kernel integration."""

import json
import unittest
from unittest.mock import patch

from integrations.semantic_kernel.doomsday_tool import (
    DoomsdayPlugin,
    DoomsdaySemanticKernelClient,
    get_doomsday_worker_status,
    list_doomsday_escrows,
    register_doomsday_plugin,
    verify_doomsday_escrow,
)


class FakeClient(DoomsdaySemanticKernelClient):
    def _get(self, path):
        if path == "/escrow/doomsday-network/bounty-guard/5":
            return {
                "issue_ref": "doomsday-network/bounty-guard#5",
                "verified_escrow": True,
                "status": "OPEN",
                "locked_doom": 1500.0,
                "evidence_level": "onchain_utxo_and_base_erc20_verified",
            }
        if path == "/escrow/list":
            return {"open_escrows": [{"issue_ref": "doomsday-network/bounty-guard#5"}], "total_locked_doom": 1500.0}
        if path == "/pool/worker/doom1worker":
            return {"address": "doom1worker", "is_active": True, "round_shares": 7}
        return {"error": "HTTP 404: Not Found", "status": "ERROR"}


class SemanticKernelTests(unittest.TestCase):
    def setUp(self):
        self.client = FakeClient()

    def test_verify_shapes_verified_response(self):
        result = self.client.verify_escrow("doomsday-network", "bounty-guard", 5)
        self.assertTrue(result["verified"])
        self.assertEqual(result["status"], "OPEN")
        self.assertEqual(result["locked_doom"], 1500.0)

    def test_invalid_input_is_local(self):
        self.assertEqual(self.client.verify_escrow("", "repo", 1)["status"], "INVALID_INPUT")
        self.assertEqual(self.client.verify_escrow("owner", "repo", 0)["status"], "INVALID_INPUT")

    def test_network_error_is_not_promoted(self):
        result = self.client.verify_escrow("example", "repo", 99)
        self.assertEqual(result["status"], "ERROR")
        self.assertNotIn("verified", result)

    def test_plain_tools(self):
        with patch("integrations.semantic_kernel.doomsday_tool._default_client", self.client):
            data = json.loads(verify_doomsday_escrow("doomsday-network", "bounty-guard", 5))
            self.assertEqual(data["locked_doom"], 1500.0)
            self.assertEqual(json.loads(list_doomsday_escrows())["total_locked_doom"], 1500.0)
            self.assertTrue(json.loads(get_doomsday_worker_status("doom1worker"))["is_active"])

    def test_optional_semantic_kernel_registration(self):
        try:
            from semantic_kernel import Kernel
        except ImportError:
            self.assertTrue(callable(register_doomsday_plugin))
            return
        kernel = Kernel()
        plugin = register_doomsday_plugin(kernel)
        self.assertEqual(set(plugin.functions), {"verify_doomsday_escrow", "list_doomsday_escrows", "get_doomsday_worker_status"})
        self.assertTrue(hasattr(DoomsdayPlugin, "verify_escrow"))


if __name__ == "__main__":
    unittest.main()
