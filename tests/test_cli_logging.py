import os
import subprocess
import sys


def run_cli(*args):
    env = os.environ.copy()
    env["PYTHONPATH"] = "src" + (
        os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else ""
    )
    return subprocess.run(
        [sys.executable, "-m", "campaignshare_fetcher.cli", *args],
        env=env,
        capture_output=True,
        text=True,
    )


def test_debug_flag_enables_debug_logging():
    p = run_cli("--dry-run", "--source", "x", "--log-level", "DEBUG")
    assert p.returncode == 0
    # DEBUG message goes to stderr
    assert "parsed args:" in p.stderr


def test_default_log_level_is_info_no_debug_line():
    p = run_cli("--dry-run", "--source", "x")
    assert p.returncode == 0
    assert "parsed args:" not in p.stderr
