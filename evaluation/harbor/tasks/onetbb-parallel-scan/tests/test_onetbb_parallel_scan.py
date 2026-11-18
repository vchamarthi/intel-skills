"""Verifier for onetbb-parallel-scan: parallel_scan prefix sum."""
import os
import re
import subprocess
import time
from pathlib import Path

import pytest

BINARY = Path("/app/scan_tbb")
SERIAL = Path("/app/scan_serial")
TARGET_SOURCE = Path("/app/scan_tbb.cpp")
LENGTHS = (1, 2, 31, 4096, 100003, 3000000)
# oneTBB ships its headers under both spellings, <tbb/...> and <oneapi/tbb/...>,
# and instruction.md names no header path, so the include check accepts both.
TBB_INCLUDE = re.compile(r'^\s*#\s*include\s*[<"](?:oneapi/)?tbb[/.]', re.MULTILINE)
TIMEOUT_SEC = 8.0


def _run(cmd):
    start = time.perf_counter()
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT_SEC + 5, check=False)
    elapsed = time.perf_counter() - start
    assert result.returncode == 0, f"{cmd} exit={result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}"
    assert "VALID" in result.stdout, f"expected VALID in stdout, got {result.stdout!r}"
    return result.stdout, elapsed


def _last_integer(text):
    nums = re.findall(r"\d+", text)
    assert nums, f"no integer validation value found in {text!r}"
    return int(nums[-1])


def test_binary_exists():
    assert BINARY.exists(), f"{BINARY} not found; compile the required oneTBB binary"
    assert os.access(BINARY, os.X_OK), f"{BINARY} is not executable"
    assert SERIAL.exists(), f"{SERIAL} not found; serial reference binary is required"
    assert os.access(SERIAL, os.X_OK), f"{SERIAL} is not executable"


@pytest.mark.parametrize("length", LENGTHS)
def test_binary_matches_serial_reference_exactly(length):
    serial_out, _ = _run([str(SERIAL), str(length)])
    parallel_out, elapsed = _run([str(BINARY), str(length)])
    serial_value = _last_integer(serial_out)
    parallel_value = _last_integer(parallel_out)
    assert parallel_value == serial_value, (
        f"parallel signature {parallel_value} differs from serial reference {serial_value}"
    )
    assert elapsed < TIMEOUT_SEC, f"execution took {elapsed:.2f}s, expected under {TIMEOUT_SEC}s"


def test_source_declares_onetbb_headers():
    assert TARGET_SOURCE.exists(), f"{TARGET_SOURCE} not found"
    text = TARGET_SOURCE.read_text(errors="replace")
    assert TBB_INCLUDE.search(text), (
        f"no oneTBB header (<tbb/...> or <oneapi/tbb/...>) included in {TARGET_SOURCE}"
    )


def test_zero_length_is_rejected():
    result = subprocess.run([str(BINARY), "0"], capture_output=True, text=True,
                            timeout=TIMEOUT_SEC, check=False)
    assert result.returncode != 0, "zero-length input must be rejected"


def _matches_reference(result, expected):
    if result.returncode != 0 or "VALID" not in result.stdout:
        return False
    try:
        actual = _last_integer(result.stdout)
    except (AssertionError, ValueError):
        return False
    return actual == expected


def test_algorithm_covers_input_and_contributes_to_result(tmp_path):
    """Reject comments, unreachable calls and discarded dummy calls, without timing claims."""
    binary = tmp_path / "instrumented"
    compile_result = subprocess.run(
        ["g++", "-O2", "-std=c++17", "-include", str(Path(__file__).with_name("algorithm_probe.hpp")),
         str(TARGET_SOURCE), "-ltbb", "-o", str(binary)],
        capture_output=True, text=True, timeout=90, check=False,
    )
    assert compile_result.returncode == 0, compile_result.stderr
    length = 100003
    reference, _ = _run([str(SERIAL), str(length)])
    expected = _last_integer(reference)
    coverage = tmp_path / "coverage.txt"
    env = {**os.environ, "DOKIMI_TBB_COVERAGE_FILE": str(coverage)}
    env.pop("DOKIMI_DISABLE_ALGORITHM", None)
    normal = subprocess.run([str(binary), str(length)], env=env,
                            capture_output=True, text=True, timeout=TIMEOUT_SEC, check=False)
    assert _matches_reference(normal, expected), "instrumented solution must preserve the result"
    covered = sum(int(n) for n in coverage.read_text().splitlines()) if coverage.exists() else 0
    assert covered >= length, f"required oneTBB algorithm covered {covered} items, expected at least {length}"
    disabled = subprocess.run([str(binary), str(length)],
                             env={**env, "DOKIMI_DISABLE_ALGORITHM": "1"},
                             capture_output=True, text=True, timeout=TIMEOUT_SEC, check=False)
    assert not _matches_reference(disabled, expected), (
        "removing the required oneTBB algorithm did not change the correct result; "
        "a discarded dummy call is not an implementation"
    )
