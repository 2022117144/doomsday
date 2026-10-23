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

    def test_claude_flow_mcp_server_and_skills(self):
        import importlib.util
        from pathlib import Path

        root = Path(__file__).resolve().parent.parent
        mcp_path = root / "integrations" / "claude-flow-mcp" / "mcp_server.py"
        skill_path = root / "integrations" / "claude-flow-mcp" / "SKILL.md"
        escrow_skill_path = root / "integrations" / "skills" / "doomsday-escrow" / "SKILL.md"

        self.assertTrue(mcp_path.exists())
        self.assertTrue(skill_path.exists())
        self.assertTrue(escrow_skill_path.exists())

        spec = importlib.util.spec_from_file_location("claude_flow_mcp_server", str(mcp_path))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        self.assertEqual(len(mod.TOOLS), 4)
        res = mod.handle_call_tool("doomsday_benchmark_pow", {"duration_seconds": 0.05})
        payload = json.loads(res["content"][0]["text"])
        self.assertGreater(payload["hashes"], 0)
        self.assertEqual(payload["algorithm"], "DoomHash-Reference-SHA256d")


if __name__ == "__main__":
    unittest.main()
