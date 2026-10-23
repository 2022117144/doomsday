"""Unit tests for Doomsday ElizaOS Plugin Integration."""

import json
from pathlib import Path
import unittest


class TestElizaOSPlugin(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parent.parent
        self.elizaos_dir = self.root / "integrations" / "elizaos"

    def test_elizaos_directory_structure(self):
        self.assertTrue(self.elizaos_dir.exists(), "integrations/elizaos directory must exist")
        
        required_files = [
            "package.json",
            "tsconfig.json",
            "README.md",
            "src/index.ts",
            "src/client.ts",
            "src/types.ts",
            "src/actions/verifyEscrow.ts",
            "src/actions/listEscrows.ts",
            "src/actions/claimFaucet.ts",
            "src/providers/escrowProvider.ts",
            "src/evaluators/escrowEvaluator.ts",
        ]
        
        for rel_path in required_files:
            file_path = self.elizaos_dir / rel_path
            self.assertTrue(file_path.exists(), f"Required file {rel_path} must exist")
            self.assertGreater(file_path.stat().st_size, 50, f"File {rel_path} must not be empty")

    def test_package_json_metadata(self):
        pkg_path = self.elizaos_dir / "package.json"
        with open(pkg_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data.get("name"), "@elizaos/plugin-doomsday")
        self.assertEqual(data.get("version"), "1.0.0")
        self.assertIn("elizaos", data.get("keywords", []))
        self.assertIn("proof-of-escrow", data.get("keywords", []))
        self.assertIn("@elizaos/core", data.get("peerDependencies", {}))

    def test_actions_and_providers_exported_in_index(self):
        index_path = self.elizaos_dir / "src" / "index.ts"
        content = index_path.read_text(encoding="utf-8")

        self.assertIn("export const doomsdayPlugin: Plugin", content)
        self.assertIn("verifyEscrowAction", content)
        self.assertIn("listEscrowsAction", content)
        self.assertIn("claimFaucetAction", content)
        self.assertIn("escrowProvider", content)
        self.assertIn("escrowEvaluator", content)

    def test_verify_escrow_action_contract(self):
        action_path = self.elizaos_dir / "src" / "actions" / "verifyEscrow.ts"
        content = action_path.read_text(encoding="utf-8")

        self.assertIn('name: "VERIFY_ESCROW"', content)
        self.assertIn("CHECK_BOUNTY_ESCROW", content)
        self.assertIn("validate:", content)
        self.assertIn("handler:", content)
        self.assertIn("examples:", content)
        self.assertIn("SAFE_WITH_ESCROW", content)
        self.assertIn("SAFE_NO_ESCROW", content)

    def test_list_escrows_action_contract(self):
        action_path = self.elizaos_dir / "src" / "actions" / "listEscrows.ts"
        content = action_path.read_text(encoding="utf-8")

        self.assertIn('name: "LIST_ESCROWS"', content)
        self.assertIn("FIND_ACTIVE_BOUNTIES", content)
        self.assertIn("https://doomsday.network/escrow/list", content)

    def test_claim_faucet_action_contract(self):
        action_path = self.elizaos_dir / "src" / "actions" / "claimFaucet.ts"
        content = action_path.read_text(encoding="utf-8")

        self.assertIn('name: "CLAIM_DOOM_FAUCET"', content)
        self.assertIn("GET_FREE_DOOM", content)
        self.assertIn("Base Mainnet", content)

    def test_readme_contains_settlement_address(self):
        readme_path = self.elizaos_dir / "README.md"
        content = readme_path.read_text(encoding="utf-8")

        self.assertIn("0x8366bce3a2d379de7656d7a67015789faf999f20", content.lower())
        self.assertIn("@elizaos/plugin-doomsday", content)
        self.assertIn("VERIFY_ESCROW", content)


if __name__ == "__main__":
    unittest.main()
