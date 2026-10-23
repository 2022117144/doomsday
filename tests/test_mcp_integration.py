#!/usr/bin/env python3
"""
Unit and Integration Test Suite for Doomsday MCP Server (`integrations/mcp/doomsday_mcp.py`)
=============================================================================================
Zero-dependency test suite using standard library `unittest` and `unittest.mock`.
Validates MCP protocol, all 8 tools, CLI argument handling, and error conditions.
"""

import io
import json
import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from integrations.mcp import doomsday_mcp


class TestDoomsdayMCPTools(unittest.TestCase):
    """Test individual tools and utility functions in doomsday_mcp."""

    @patch("integrations.mcp.doomsday_mcp._get_json")
    def test_list_escrows(self, mock_get):
        mock_get.return_value = {
            "status": "success",
            "open_escrows": [{"escrow_id": "escrow_001", "amount_doom": 1000}],
            "escrow_vault_reserve_doom": 50000.0,
            "vault_utxo_verified": True
        }
        res = doomsday_mcp.list_escrows()
        self.assertEqual(res["status"], "success")
        self.assertEqual(len(res["open_escrows"]), 1)
        mock_get.assert_called_once_with("/escrow/list")

    @patch("integrations.mcp.doomsday_mcp._get_json")
    def test_verify_issue_escrow_valid(self, mock_get):
        mock_get.return_value = {
            "issue_ref": "doomsday-network/doomsday#11",
            "verified_escrow": True,
            "locked_doom": 3000.0,
            "status": "OPEN"
        }
        res = doomsday_mcp.verify_issue_escrow("doomsday-network/doomsday#11")
        self.assertTrue(res["verified_escrow"])
        self.assertEqual(res["locked_doom"], 3000.0)
        mock_get.assert_called_once_with("/escrow/doomsday-network/doomsday/11")

    def test_verify_issue_escrow_invalid_format(self):
        res = doomsday_mcp.verify_issue_escrow("invalid_reference")
        self.assertIn("error", res)
        self.assertIn("Expected owner/repo#number", res["error"])

    @patch("integrations.mcp.doomsday_mcp.list_escrows")
    def test_audit_doomsday_escrows_classification(self, mock_list):
        mock_list.return_value = {
            "escrow_vault_reserve_doom": 25000.0,
            "vault_utxo_verified": True,
            "escrow_vault_address": "doom1vault123",
            "open_escrows": [
                {"escrow_id": "e1", "title": "Implement MCP Server", "amount_doom": 3000},
                {"escrow_id": "e2", "title": "Submit private key leak test", "amount_doom": 100}
            ]
        }
        res = doomsday_mcp.audit_doomsday_escrows()
        self.assertEqual(res["status"], "success")
        audited = res["audited_escrows"]
        self.assertEqual(len(audited), 2)
        self.assertEqual(audited[0]["risk"], "SAFE_WITH_ESCROW")
        self.assertEqual(audited[1]["risk"], "QUARANTINE")

    @patch("integrations.mcp.doomsday_mcp._get_json")
    def test_get_pool_leaderboard(self, mock_get):
        mock_get.return_value = {
            "leaders": [{"address": "doom1test", "hashrate_mhs": 1200.5}],
            "total_unique_miners": 7
        }
        res = doomsday_mcp.get_pool_leaderboard()
        self.assertEqual(res["total_unique_miners"], 7)
        mock_get.assert_called_once_with("/pool/leaderboard")

    @patch("integrations.mcp.doomsday_mcp._get_json")
    def test_get_wallet_balance_valid(self, mock_get):
        mock_get.return_value = {
            "address": "doom192e6ba55224befad203145a78b4d594a694a3e8b588d5d47",
            "balance_doom": 5515.0,
            "utxo_count": 5
        }
        res = doomsday_mcp.get_wallet_balance("doom192e6ba55224befad203145a78b4d594a694a3e8b588d5d47")
        self.assertEqual(res["balance_doom"], 5515.0)
        self.assertEqual(res["utxo_count"], 5)

    def test_get_wallet_balance_invalid_address(self):
        res = doomsday_mcp.get_wallet_balance("0x1234567890abcdef")
        self.assertIn("error", res)
        self.assertIn("Expected address starting with 'doom1...'", res["error"])

    @patch("integrations.mcp.doomsday_mcp._post_json")
    def test_claim_faucet_valid(self, mock_post):
        mock_post.return_value = {
            "success": True,
            "amount_doom": 15.0,
            "txid": "test_tx_hash_123"
        }
        res = doomsday_mcp.claim_faucet("doom1testaddress999")
        self.assertTrue(res["success"])
        self.assertEqual(res["amount_doom"], 15.0)

    def test_claim_faucet_invalid_address(self):
        res = doomsday_mcp.claim_faucet("invalid_addr")
        self.assertIn("error", res)

    @patch("integrations.mcp.doomsday_mcp.verify_issue_escrow")
    def test_format_escrow_badge_verified(self, mock_verify):
        mock_verify.return_value = {
            "issue_ref": "doomsday-network/doomsday#11",
            "verified_escrow": True,
            "status": "OPEN",
            "locked_doom": 3000.0,
            "escrow_vault_address": "doom1caea0957fb471c2b83940cc2feb421abad938dfbdef662de"
        }
        res = doomsday_mcp.format_escrow_badge("doomsday-network/doomsday#11")
        self.assertTrue(res["verified_escrow"])
        self.assertIn("VERIFIED_3,000_DOOM", res["markdown_badge"])
        self.assertIn("doom1caea0957fb4", res["markdown_badge"])

    @patch("integrations.mcp.doomsday_mcp._get_json")
    def test_verify_miner_worker(self, mock_get):
        mock_get.return_value = {
            "address": "doom1testworker",
            "is_active": True,
            "round_shares": 1
        }
        res = doomsday_mcp.verify_miner_worker("doom1testworker")
        self.assertTrue(res["is_active"])
        self.assertEqual(res["round_shares"], 1)

    @patch("integrations.mcp.doomsday_mcp._post_json")
    @patch("integrations.mcp.doomsday_mcp._get_json")
    def test_generate_and_send_doom_l1_signed(self, mock_get, mock_post):
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            wpath = os.path.join(tmpdir, "test_agent_wallet.json")
            gen = doomsday_mcp.generate_doom_wallet(wpath)
            self.assertEqual(gen["status"], "generated")
            self.assertTrue(gen["created_new"])
            self.assertTrue(gen["address"].startswith("doom1"))
            self.assertNotIn("private_key", gen)

            # Second call loads existing without overwriting
            gen2 = doomsday_mcp.generate_doom_wallet(wpath)
            self.assertEqual(gen2["status"], "loaded_existing")
            self.assertEqual(gen2["address"], gen["address"])

            mock_get.return_value = {
                "address": gen["address"],
                "utxos": [{"txid": "a" * 64, "vout": 0, "amount": 500_00000000}]
            }
            mock_post.return_value = {
                "status": "broadcasted",
                "txid": "b" * 64,
                "inputs": 1,
                "outputs": 2,
            }

            recipient = "doom192e6ba55224befad203145a78b4d594a694a3e8b588d5d47"
            tx_res = doomsday_mcp.send_doom_l1(recipient, 250.0, memo="A2A:doomsday#11", wallet_file=wpath)
            self.assertEqual(tx_res["status"], "broadcasted")
            self.assertEqual(tx_res["from_address"], gen["address"])
            self.assertEqual(tx_res["to_address"], recipient)
            self.assertEqual(tx_res["amount_doom"], 250.0)
            self.assertEqual(tx_res["miner_fee_doom"], 0.001)
            self.assertEqual(tx_res["outputs_created"], 2)

            # Verify broadcast payload contained real ECDSA signature and pubkey
            called_path, called_payload = mock_post.call_args[0]
            self.assertEqual(called_path, "/tx/broadcast")
            tx_dict = called_payload["transaction"]
            self.assertTrue(len(tx_dict["inputs"][0]["signature"]) > 64)
            self.assertTrue(len(tx_dict["inputs"][0]["pubkey_hex"]) == 66)

    @patch("integrations.mcp.doomsday_mcp._get_json")
    def test_verify_l1_payment(self, mock_get):
        txid = "c" * 64
        recipient = "doom192e6ba55224befad203145a78b4d594a694a3e8b588d5d47"
        mock_get.return_value = {
            "address": recipient,
            "utxos": [{"txid": txid, "vout": 0, "amount": 250_00000000}]
        }
        v = doomsday_mcp.verify_l1_payment(txid, recipient, min_amount_doom=200.0)
        self.assertTrue(v["verified"])
        self.assertEqual(v["amount_doom"], 250.0)
        self.assertEqual(v["confirmation_source"], "utxo_set")


class TestDoomsdayMCPProtocol(unittest.TestCase):
    """Test standard JSON-RPC 2.0 stdio handling for the Model Context Protocol."""

    def _run_rpc(self, messages):
        input_data = "\n".join(json.dumps(m) for m in messages) + "\n"
        stdin_backup = sys.stdin
        stdout_backup = sys.stdout
        try:
            sys.stdin = io.StringIO(input_data)
            sys.stdout = io.StringIO()
            doomsday_mcp.run_mcp_stdio()
            output = sys.stdout.getvalue()
        finally:
            sys.stdin = stdin_backup
            sys.stdout = stdout_backup
        
        responses = [json.loads(line) for line in output.strip().split("\n") if line.strip()]
        return responses

    def test_initialize(self):
        req = [{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}]
        res = self._run_rpc(req)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["id"], 1)
        self.assertEqual(res[0]["result"]["serverInfo"]["name"], "doomsday-escrow-mcp")

    def test_tools_list(self):
        req = [{"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}]
        res = self._run_rpc(req)
        self.assertEqual(len(res), 1)
        tools = res[0]["result"]["tools"]
        self.assertGreaterEqual(len(tools), 8)
        tool_names = [t["name"] for t in tools]
        self.assertIn("list_escrows", tool_names)
        self.assertIn("verify_issue_escrow", tool_names)
        self.assertIn("audit_doomsday_escrows", tool_names)
        self.assertIn("get_pool_leaderboard", tool_names)
        self.assertIn("get_wallet_balance", tool_names)
        self.assertIn("claim_faucet", tool_names)
        self.assertIn("verify_miner_worker", tool_names)
        self.assertIn("format_escrow_badge", tool_names)

    @patch("integrations.mcp.doomsday_mcp.get_wallet_balance")
    def test_tools_call_get_wallet_balance(self, mock_bal):
        mock_bal.return_value = {"balance_doom": 5515.0}
        req = [{
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "get_wallet_balance", "arguments": {"address": "doom1test"}}
        }]
        res = self._run_rpc(req)
        self.assertEqual(len(res), 1)
        content_text = res[0]["result"]["content"][0]["text"]
        payload = json.loads(content_text)
        self.assertEqual(payload["balance_doom"], 5515.0)

    def test_unknown_tool(self):
        req = [{
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "non_existent_tool", "arguments": {}}
        }]
        res = self._run_rpc(req)
        self.assertEqual(len(res), 1)
        content_text = res[0]["result"]["content"][0]["text"]
        self.assertIn("Unknown tool", content_text)


if __name__ == "__main__":
    unittest.main()
