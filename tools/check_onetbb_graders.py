#!/usr/bin/env python3
# Copyright (C) 2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
"""Exercise oneTBB task graders against references and deliberately invalid controls.

Needs Docker, no model or credentials. This checks grader discrimination, not speedup.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
import uuid
from pathlib import Path

TASKS = ("onetbb-parallel-reduce", "onetbb-parallel-scan")
CONTROLS = ("oracle", "tbb-alias", "alternate-api", "null", "serial", "dead-call", "dummy-call", "wrong-length", "zero-accepted")


def alternate_source(task: Path) -> str:
    """Exercise both body and functional overloads, rather than enforce oracle style."""
    stem = task.name.removeprefix("onetbb-parallel-")
    source = (task / "environment" / f"{stem}.cpp").read_text()
    if stem == "scan":
        start = source.index("    std::int64_t running = 0;")
        end = source.index("    std::uint64_t signature", start)
        replacement = '''    tbb::parallel_scan(tbb::blocked_range<std::size_t>(0, n), std::int64_t{0},
        [&](const auto& range, std::int64_t partial, bool is_final_scan) {
            for (std::size_t i = range.begin(); i != range.end(); ++i) {
                partial += input[i];
                if (is_final_scan) prefix[i] = partial;
            }
            return partial;
        }, std::plus<std::int64_t>{});

'''
    else:
        body = '''struct Reduction {
    const std::vector<std::int64_t>* data;
    long double sum = 0, sumsq = 0;
    std::int64_t minv = std::numeric_limits<std::int64_t>::max();
    std::int64_t maxv = std::numeric_limits<std::int64_t>::min();
    explicit Reduction(const std::vector<std::int64_t>& values) : data(&values) {}
    Reduction(Reduction& other, tbb::split) : data(other.data) {}
    void operator()(const tbb::blocked_range<std::size_t>& range) {
        for (std::size_t i = range.begin(); i != range.end(); ++i) {
            auto v = (*data)[i]; sum += v; sumsq += static_cast<long double>(v) * v;
            minv = std::min(minv, v); maxv = std::max(maxv, v);
        }
    }
    void join(const Reduction& other) {
        sum += other.sum; sumsq += other.sumsq;
        minv = std::min(minv, other.minv); maxv = std::max(maxv, other.maxv);
    }
};

'''
        source = source.replace("int main(", body + "int main(", 1)
        start = source.index("    long double sum = 0.0;", source.index("int main("))
        end = source.index("    const long double signature", start)
        replacement = '''    Reduction result(data);
    tbb::parallel_reduce(tbb::blocked_range<std::size_t>(0, n), result);
    const auto sum = result.sum, sumsq = result.sumsq;
    const auto minv = result.minv, maxv = result.maxv;

'''
    return "#include <oneapi/tbb.h>\n#include <functional>\n#include <limits>\n#include <algorithm>\n" + source[:start] + replacement + source[end:]


def invalid_source(task: Path, kind: str) -> str:
    stem = task.name.removeprefix("onetbb-parallel-")
    source = (task / "environment" / f"{stem}.cpp").read_text()
    headers = "#include <oneapi/tbb.h>\n#include <functional>\n"
    marker = "// parallel_reduce parallel_scan is_final_scan\n"
    if kind in ("dummy-call", "dead-call"):
        if stem == "reduce":
            call = "tbb::parallel_reduce(tbb::blocked_range<std::size_t>(0, n), 0LL, [](const auto&, long long x) { return x; }, std::plus<long long>{});"
        else:
            call = "tbb::parallel_scan(tbb::blocked_range<std::size_t>(0, n), 0LL, [](const auto&, long long x, bool) { return x; }, std::plus<long long>{});"
        if kind == "dead-call":
            call = "if (false) { " + call + " }"
        source = source.replace("if (n == 0) return 2;", "if (n == 0) return 2;\n    " + call)
    if kind == "wrong-length":
        default = "4000000" if stem == "reduce" else "3000000"
        source = source.replace("argc > 1 ? std::strtoull(argv[1], nullptr, 10) : " + default, default)
    return headers + marker + source


def check_task(task: Path, controls: list[str], docker: str, log_dir: Path) -> list[dict]:
    tag = "intel-skills-grader:" + task.name
    container = "skills-grader-" + uuid.uuid4().hex[:12]
    log_dir.mkdir(parents=True, exist_ok=True)

    def run(args: list[str], *, check: bool = True, timeout: int = 180):
        result = subprocess.run([docker, *args], capture_output=True, text=True,
                                timeout=timeout, check=False)
        with (log_dir / "docker.log").open("a") as f:
            f.write(json.dumps(args) + "\n" + result.stdout + result.stderr)
        if check and result.returncode:
            raise RuntimeError(f"docker {args[0]} failed; see {log_dir / 'docker.log'}")
        return result

    run(["build", "-q", "-t", tag, str(task / "environment")], timeout=600)
    image_id = run(["image", "inspect", "--format", "{{.Id}}", tag]).stdout.strip()
    rows = []
    try:
        run(["run", "-d", "--name", container, "--network", "none", "--cpus", "2",
             "--memory", "2g", "--pids-limit", "256", tag, "sleep", "1800"])
        run(["cp", str(task / "tests") + "/.", container + ":/tests"])
        run(["cp", str(task / "solution") + "/.", container + ":/solution"])
        stem = task.name.removeprefix("onetbb-parallel-")
        target = f"/app/{stem}_tbb.cpp"
        with tempfile.TemporaryDirectory(prefix="onetbb-grader-control-") as tmp:
            source_path = Path(tmp) / f"{stem}_tbb.cpp"
            for kind in controls:
                run(["exec", container, "rm", "-f", target, f"/app/{stem}_tbb", "/logs/verifier/reward.txt"])
                if kind in ("oracle", "tbb-alias", "zero-accepted"):
                    run(["exec", container, "bash", "/solution/solve.sh"])
                    if kind != "oracle":
                        run(["cp", f"{container}:{target}", str(source_path)])
                        source = source_path.read_text()
                        if kind == "tbb-alias":
                            source = source.replace("<oneapi/tbb/", "<tbb/").replace("oneapi::tbb::", "tbb::")
                        else:
                            old = "if (n == 0) return 2;"
                            assert old in source, f"reference zero guard changed in {task.name}"
                            source = source.replace(old, 'if (n == 0) { std::cout << "VALID 0\\n"; return 0; }')
                        source_path.write_text(source)
                elif kind == "alternate-api":
                    source_path.write_text(alternate_source(task))
                elif kind != "null":
                    source_path.write_text(invalid_source(task, kind))
                if kind not in ("oracle", "null"):
                    run(["cp", str(source_path), f"{container}:{target}"])
                    run(["exec", container, "g++", "-O3", "-std=c++17", target,
                         "-ltbb", "-o", f"/app/{stem}_tbb"])
                verdict = run(["exec", container, "bash", "/tests/test.sh"], check=False)
                reward = run(["exec", container, "cat", "/logs/verifier/reward.txt"]).stdout.strip()
                expected = kind in ("oracle", "tbb-alias", "alternate-api")
                accepted = verdict.returncode == 0 and reward == "1"
                consistent = (verdict.returncode == 0 and reward == "1") or (verdict.returncode != 0 and reward == "0")
                rows.append({"task": task.name, "control": kind, "image_id": image_id, "expected_accept": expected,
                             "accepted": accepted, "verifier_exit": verdict.returncode,
                             "reward": reward, "pass": consistent and accepted == expected})
                (log_dir / (kind + ".log")).write_text(verdict.stdout + verdict.stderr)
    finally:
        run(["rm", "-f", container], check=False, timeout=60)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks-root", type=Path, default=Path("evaluation/harbor/tasks"))
    parser.add_argument("--controls", default=",".join(CONTROLS))
    parser.add_argument("--out", type=Path,
                        default=Path(tempfile.gettempdir()) / "onetbb-grader-controls" / "results.json")
    parser.add_argument("--docker", default="docker")
    args = parser.parse_args()
    controls = args.controls.split(",")
    if not controls or any(c not in CONTROLS for c in controls):
        parser.error("controls must be chosen from " + ",".join(CONTROLS))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    rows, hashes = [], {}
    for name in TASKS:
        task = args.tasks_root / name
        hashes[name] = {str(p.relative_to(task)): hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in sorted((task / "tests").iterdir()) if p.is_file()}
        rows.extend(check_task(task, controls, args.docker, args.out.parent / name))
    payload = {"scope": "real Docker, no models; correctness/discrimination only, 2 CPU quota",
               "driver_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               "grader_sha256": hashes, "results": rows, "passed": all(r["pass"] for r in rows)}
    args.out.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps({"passed": payload["passed"], "checks": len(rows), "results": str(args.out)}))
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
