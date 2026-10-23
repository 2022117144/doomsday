"""Unit tests for Doomsday LangChain Tool integration."""
import unittest
from integrations.langchain.doomsday_tool import DoomsdayEscrowClient


class TestDoomsdayEscrowClient(unittest.TestCase):
    def setUp(self):
        self.client = DoomsdayEscrowClient()

    def test_client_initialization(self):
        self.assertEqual(self.client.base_url, "https://doomsday.network")
        self.assertEqual(self.client.timeout, 15)

    def test_verify_bounty_structure(self):
        res = self.client.verify_bounty("doomsday-network", "doomsday", 11)
        self.assertIsInstance(res, dict)


if __name__ == "__main__":
    unittest.main()
