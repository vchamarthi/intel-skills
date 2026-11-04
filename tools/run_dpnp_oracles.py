# Copyright (C) 2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0

"""Qualify all five dpnp oracle/verifier pairs on a native Linux x86 Docker host."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

TASKS = ("dpnp-device-fallback", "dpnp-fft-pipeline", "dpnp-linalg-matmul",
         "dpnp-migration-replace-numpy", "dpnp-reduction-stats")


def _safe_task(task: Path) -> Path:
    if task.is_symlink() or any(path.is_symlink() for path in task.rglob("*")):
        raise ValueError(f"oracle task contains a symlink: {task}")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", task.name):
        raise ValueError(f"unsafe task name: {task.name}")
    for relative in ("environment/Dockerfile", "solution/solve.sh", "tests/test.sh"):
        if not (task / relative).is_file():
            raise ValueError(f"missing oracle input: {task / relative}")
    return task.resolve()


def run_task(task: Path, out: Path, *, execute: Callable[..., Any] = subprocess.run) -> dict[str, Any]:
    task = _safe_task(task)
    output = out / task.name
    logs = output / "logs"
    verifier_logs = logs / "verifier"
    verifier_logs.mkdir(parents=True, exist_ok=True)
    # Container root has no DAC override; bind mounts retain the runner UID.
    # Only this dedicated output directory needs cross-UID write access.
    verifier_logs.chmod(0o1777)
    image = f"dokimi-dpnp-oracle:{task.name}"
    started = time.monotonic()
    build = execute(["docker", "build", "--iidfile", str(output / "image-id.txt"), "-t", image,
                     str(task / "environment")], capture_output=True, text=True, timeout=900)
    (output / "build.log").write_text(build.stdout + build.stderr)
    receipt: dict[str, Any] = {"task": task.name, "image": image, "build_exit": build.returncode,
                              "run_exit": None, "reward": None, "passed": False}
    if build.returncode == 0:
        mounts = [(task / "solution", "/solution", True), (task / "tests", "/tests", True), (logs, "/logs", False)]
        args = ["docker", "run", "--rm", "--network", "none", "--cap-drop", "ALL", "--security-opt", "no-new-privileges"]
        for source, destination, readonly in mounts:
            args.extend(["--mount", f"type=bind,src={source},dst={destination}" + (",readonly" if readonly else "")])
        args.extend([image, "bash", "-c", "bash /solution/solve.sh && bash /tests/test.sh"])
        trial = execute(args, capture_output=True, text=True, timeout=600)
        (output / "verifier.log").write_text(trial.stdout + trial.stderr)
        reward = _reward(logs / "verifier/reward.txt")
        receipt.update(run_exit=trial.returncode, reward=reward, passed=trial.returncode == 0 and reward == 1)
    receipt["elapsed_sec"] = round(time.monotonic() - started, 3)
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def _reward(path: Path) -> float | None:
    try:
        return float(path.read_text().strip())
    except (OSError, ValueError):
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    root, out = args.root.resolve(), args.out.absolute()
    if out.exists():
        raise ValueError("oracle output must be a fresh directory")
    task_root = root / "evaluation/harbor/tasks"
    for path in (root / "evaluation", root / "evaluation/harbor", task_root):
        if path.is_symlink():
            raise ValueError(f"oracle tasks parent is a symlink: {path}")
    tasks = [_safe_task(task_root / name) for name in TASKS]
    out.mkdir(parents=True)
    receipts = []
    for task in tasks:
        receipt = run_task(task, out)
        receipts.append(receipt)
        print(json.dumps(receipt), flush=True)
    (out / "summary.json").write_text(json.dumps(receipts, indent=2) + "\n")
    return 0 if all(receipt["passed"] for receipt in receipts) else 1


if __name__ == "__main__":
    raise SystemExit(main())
