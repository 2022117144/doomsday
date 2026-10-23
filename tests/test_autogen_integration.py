"""Unit tests for Doomsday Microsoft AutoGen Integration."""

import json
import unittest
from integrations.autogen.doomsday_tool import (
    DoomsdayAutoGenClient,
    verify_doomsday_escrow,
    list_doomsday_escrows,
    claim_doomsday_faucet,
    register_doomsday_tools,
)


class TestAutoGenIntegration(unittest.TestCase):
    def setUp(self):
        self.client = DoomsdayAutoGenClient()

    def test_client_init(self):
        self.assertEqual(self.client.base_url, "https://doomsday.network")
        self.assertEqual(self.client.timeout, 15)

    def test_verify_doomsday_escrow_tool(self):
        res_str = verify_doomsday_escrow("doomsday-network", "doomsday", 11)
        self.assertIsInstance(res_str, str)
        data = json.loads(res_str)
        self.assertTrue(data.get("verified"))
        self.assertEqual(data.get("status"), "SAFE_WITH_ESCROW")
        self.assertEqual(data.get("reward_doom"), 3000.0)
        self.assertIn("doom1caea", data.get("vault_address", ""))

    def test_list_doomsday_escrows_tool(self):
        res_str = list_doomsday_escrows()
        self.assertIsInstance(res_str, str)
        data = json.loads(res_str)
        self.assertIn("open_escrows", data)
        self.assertGreaterEqual(len(data.get("open_escrows", [])), 1)

    def test_claim_doomsday_faucet_tool(self):
        res_str = claim_doomsday_faucet("0x8366bce3a2d379de7656d7a67015789faf999f20")
        self.assertIsInstance(res_str, str)
        data = json.loads(res_str)
        self.assertIn("recipient", data)

    def test_register_doomsday_tools_graceful(self):
        # Should not crash even without pyautogen installed in the minimal environment
        class MockAgent:
            pass

        agent = MockAgent()
        register_doomsday_tools(agent)


if __name__ == "__main__":
    unittest.main()
