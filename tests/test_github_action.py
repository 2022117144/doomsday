"""Unit tests for Doomsday Proof-of-Escrow GitHub Action."""

import json
import os
import subprocess
import sys
import unittest


class TestDoomsdayGitHubAction(unittest.TestCase):
    def setUp(self):
        self.entrypoint = os.path.abspath("actions/verify-escrow/entrypoint.py")
        self.assertTrue(os.path.exists(self.entrypoint), f"Missing entrypoint: {self.entrypoint}")

    def test_entrypoint_valid_run(self):
        env = os.environ.copy()
        env["INPUT_ISSUE_NUMBER"] = "11"
        env["INPUT_REPOSITORY"] = "doomsday-network/doomsday"
        env["INPUT_API_URL"] = "https://doomsday.network"
        env["INPUT_POST_BADGE_COMMENT"] = "false"
        env["INPUT_FAIL_ON_UNVERIFIED"] = "false"

        res = subprocess.run([sys.executable, self.entrypoint], env=env, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        self.assertIn("[OUTPUT] is-verified=", res.stdout)
        self.assertIn("[OUTPUT] status=", res.stdout)
        self.assertIn("[OUTPUT] collateral-doom=", res.stdout)

    def test_entrypoint_invalid_inputs(self):
        env = os.environ.copy()
        env["INPUT_ISSUE_NUMBER"] = "not_a_number"
        env["INPUT_REPOSITORY"] = "invalid"

        res = subprocess.run([sys.executable, self.entrypoint], env=env, capture_output=True, text=True)
        self.assertEqual(res.returncode, 1)
        self.assertIn("[ERROR]", res.stdout)


if __name__ == "__main__":
    unittest.main()
