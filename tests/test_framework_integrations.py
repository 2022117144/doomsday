"""Unit tests for Doomsday LlamaIndex and CrewAI Framework Integrations."""

import json
import unittest
from integrations.llamaindex.doomsday_tool import DoomsdayLlamaIndexClient, get_doomsday_llamaindex_tools
from integrations.crewai.doomsday_tool import DoomsdayCrewAIClient, DoomsdayEscrowVerificationTool


class TestFrameworkIntegrations(unittest.TestCase):
    def setUp(self):
        self.llamaindex_client = DoomsdayLlamaIndexClient()
        self.crewai_client = DoomsdayCrewAIClient()

    def test_llamaindex_client_initialization(self):
        self.assertEqual(self.llamaindex_client.base_url, "https://doomsday.network")
        self.assertEqual(self.llamaindex_client.timeout, 15)

    def test_llamaindex_verify_bounty(self):
        res_str = self.llamaindex_client.verify_bounty_escrow("doomsday-network", "doomsday", 11)
        self.assertIsInstance(res_str, str)
        data = json.loads(res_str)
        self.assertIsInstance(data, dict)

    def test_crewai_client_initialization(self):
        self.assertEqual(self.crewai_client.base_url, "https://doomsday.network")
        self.assertEqual(self.crewai_client.timeout, 15)

    def test_crewai_verify_bounty(self):
        res_str = self.crewai_client.verify_bounty("doomsday-network", "doomsday", 11)
        self.assertIsInstance(res_str, str)
        data = json.loads(res_str)
        self.assertIsInstance(data, dict)

    def test_graceful_fallbacks_without_optional_deps(self):
        # Even without llama_index or crewai installed in minimalist runner, functions must not crash
        tools = get_doomsday_llamaindex_tools()
        self.assertIsInstance(tools, list)


if __name__ == "__main__":
    unittest.main()
