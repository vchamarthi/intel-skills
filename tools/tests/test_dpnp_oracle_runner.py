# Copyright (C) 2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0

"""Oracle qualification records verifier reward and rejects unsafe host mounts."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_dpnp_oracles as runner


class DpnpOracleRunner(unittest.TestCase):
    def task(self, root):
        task = root / "demo"
        for name in ("environment", "solution", "tests"):
            (task / name).mkdir(parents=True)
        (task / "environment/Dockerfile").write_text("FROM scratch\n")
        (task / "solution/solve.sh").write_text("true\n")
        (task / "tests/test.sh").write_text("true\n")
        return task

    def test_verifier_reward_is_required_even_when_docker_exits_zero(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            task = self.task(root)
            def docker(args, **_kwargs):
                return subprocess.CompletedProcess(args, 0, "", "")
            result = runner.run_task(task, root / "out", execute=docker)
            self.assertFalse(result["passed"])
            self.assertIsNone(result["reward"])

    def test_oracle_pass_requires_reward_one_and_offline_container(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            task = self.task(root)
            commands = []
            def docker(args, **_kwargs):
                commands.append(args)
                if args[1] == "run":
                    (root / "out/demo/logs/verifier").mkdir(parents=True)
                    (root / "out/demo/logs/verifier/reward.txt").write_text("1\n")
                return subprocess.CompletedProcess(args, 0, "passed", "")
            result = runner.run_task(task, root / "out", execute=docker)
            self.assertTrue(result["passed"])
            run = commands[1]
            self.assertEqual(run[run.index("--network") + 1], "none")
            self.assertEqual(run[run.index("--cap-drop") + 1], "ALL")
            self.assertIn("no-new-privileges", run)

    def test_symlink_is_rejected_before_docker_gets_host_mounts(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            task = self.task(root)
            (task / "solution/escape").symlink_to("/")
            calls = []
            with self.assertRaisesRegex(ValueError, "symlink"):
                runner.run_task(task, root / "out", execute=lambda *args, **kwargs: calls.append(args))
            self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
