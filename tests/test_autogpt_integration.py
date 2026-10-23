"""Unit tests for Doomsday AutoGPT Proof-of-Escrow Block."""

import unittest
from integrations.autogpt.doomsday_block import DoomsdayAutoGPTClient, DoomsdayProofOfEscrowBlock


class TestAutoGPTIntegration(unittest.TestCase):
    def setUp(self):
        self.block = DoomsdayProofOfEscrowBlock()
        self.client = DoomsdayAutoGPTClient()

    def test_client_init(self):
        self.assertEqual(self.client.base_url, "https://doomsday.network")
        self.assertEqual(self.client.timeout, 15)

    def test_block_verify_escrow_valid(self):
        result = self.block.run(
            action="verify_escrow",
            repo_owner="doomsday-network",
            repo_name="doomsday",
            issue_number=11,
        )
        self.assertTrue(result.get("verified"))
        self.assertEqual(result.get("status"), "SAFE_WITH_ESCROW")
        self.assertEqual(result.get("reward_doom"), 3000.0)
        self.assertIn("doom1caea", result.get("vault_address", ""))
        self.assertIn("Doomsday_Escrow", result.get("badge_markdown", ""))

    def test_block_verify_escrow_missing_params(self):
        result = self.block.run(action="verify_escrow")
        self.assertFalse(result.get("success", True))
        self.assertIn("Missing required parameters", result.get("error", ""))

    def test_block_list_escrows(self):
        result = self.block.run(action="list_escrows")
        self.assertTrue(result.get("success"))
        self.assertGreaterEqual(result.get("total_open", 0), 1)
        self.assertIsInstance(result.get("open_escrows"), list)

    def test_block_unknown_action(self):
        result = self.block.run(action="invalid_action_name")
        self.assertFalse(result.get("success", True))
        self.assertIn("Unknown action", result.get("error", ""))


if __name__ == "__main__":
    unittest.main()
