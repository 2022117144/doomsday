"""Tests for the OpenAI Agents SDK Proof-of-Escrow integration."""

import unittest

from integrations.openai_agents.doomsday_tool import DoomsdayEscrowClient, read_escrow


class FakeClient(DoomsdayEscrowClient):
    def __init__(self, response):
        super().__init__()
        self.response = response

    def verify(self, owner, repo, issue):
        return self.response


class ReadEscrowTests(unittest.TestCase):
    def test_verified_escrow_is_parsed(self):
        row = read_escrow(
            FakeClient(
                {
                    "issue_ref": "doomsday-network/doomsday#11",
                    "status": "OPEN",
                    "locked_doom": 3000.0,
                    "verified_escrow": True,
                    "evidence_level": "onchain_utxo_and_base_erc20_verified",
                }
            ),
            "doomsday-network/doomsday#11",
        )
        self.assertEqual(row.status, "OPEN")
        self.assertEqual(row.locked_doom, 3000.0)
        self.assertTrue(row.verified_escrow)

    def test_error_is_not_promoted_to_escrow(self):
        row = read_escrow(FakeClient({"error": "network down"}), "owner/repo#1")
        self.assertEqual(row.status, "ERROR")
        self.assertEqual(row.locked_doom, 0.0)
        self.assertFalse(row.verified_escrow)

    def test_invalid_input_is_rejected_locally(self):
        client = DoomsdayEscrowClient()
        self.assertEqual(client.verify("", "repo", 1)["status"], "INVALID_INPUT")
        self.assertEqual(client.verify("owner", "repo", "x")["status"], "INVALID_INPUT")

    def test_optional_agents_adapter_has_expected_tool_shape(self):
        try:
            from agents import FunctionTool
        except ImportError:
            self.skipTest("openai-agents is an optional dependency")

        from integrations.openai_agents import doomsday_tool

        tool = doomsday_tool.verify_doomsday_escrow
        self.assertIsInstance(tool, FunctionTool)
        self.assertEqual(tool.name, "verify_doomsday_escrow")
        schema = tool.params_json_schema
        self.assertEqual(set(schema["required"]), {"owner", "repo", "issue"})
        self.assertEqual(schema["properties"]["issue"]["type"], "integer")


if __name__ == "__main__":
    unittest.main()
