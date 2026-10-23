"""Unit tests for Doomsday OpenAI Agents SDK & MCP Integration."""

import importlib.util
import json
import os
import unittest

_MODULE_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "integrations", "openai-agents", "doomsday_tool.py")
)
_SPEC = importlib.util.spec_from_file_location("doomsday_openai_agents_tool", _MODULE_PATH)
assert _SPEC and _SPEC.loader
doomsday_tool = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(doomsday_tool)


class TestOpenAIAgentsIntegration(unittest.TestCase):
    def setUp(self):
        self.client = doomsday_tool.DoomsdayOpenAIAgentClient()

    def test_client_defaults(self):
        self.assertEqual(self.client.base_url, "https://doomsday.network")
        self.assertEqual(len(doomsday_tool.OPENAI_TOOLS_SCHEMA), 3)

    def test_verify_escrow_issue_11(self):
        res_str = doomsday_tool.verify_doomsday_escrow("doomsday-network", "doomsday", 11)
        data = json.loads(res_str)
        self.assertTrue(data.get("verified"))
        self.assertEqual(data.get("status"), "SAFE_WITH_ESCROW")
        self.assertEqual(data.get("reward_doom"), 3000.0)
        self.assertEqual(data.get("issue_ref"), "doomsday-network/doomsday#11")

    def test_verify_unescrowed_issue(self):
        res_str = doomsday_tool.verify_doomsday_escrow("example-org", "example-repo", 99999)
        data = json.loads(res_str)
        self.assertFalse(data.get("verified"))
        self.assertEqual(data.get("status"), "SAFE_NO_ESCROW")

    def test_list_escrows(self):
        res_str = doomsday_tool.list_doomsday_escrows()
        data = json.loads(res_str)
        self.assertIn("open_escrows", data)
        self.assertGreaterEqual(len(data["open_escrows"]), 1)

    def test_dispatch_tool_call(self):
        out = doomsday_tool.dispatch_tool_call(
            "verify_doomsday_escrow",
            json.dumps({"owner": "doomsday-network", "repo": "bounty-guard", "issue_number": 5}),
        )
        parsed = json.loads(out)
        self.assertTrue(parsed.get("verified"))
        self.assertEqual(parsed.get("reward_doom"), 1500.0)

    def test_mcp_jsonrpc_lifecycle(self):
        init_resp = doomsday_tool.handle_mcp_request({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
        self.assertEqual(init_resp["result"]["serverInfo"]["name"], "doomsday-openai-agents-mcp")

        list_resp = doomsday_tool.handle_mcp_request({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        tool_names = [t["name"] for t in list_resp["result"]["tools"]]
        self.assertIn("verify_doomsday_escrow", tool_names)
        self.assertIn("list_doomsday_escrows", tool_names)
        self.assertIn("claim_doomsday_faucet", tool_names)

        call_resp = doomsday_tool.handle_mcp_request(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "verify_doomsday_escrow",
                    "arguments": {"owner": "doomsday-network", "repo": "doomsday", "issue_number": 11},
                },
            }
        )
        content_text = call_resp["result"]["content"][0]["text"]
        payload = json.loads(content_text)
        self.assertTrue(payload["verified"])


if __name__ == "__main__":
    unittest.main()
