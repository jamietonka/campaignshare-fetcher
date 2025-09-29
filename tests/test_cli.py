import os
import subprocess
import sys


def run_cli(*args):
    env = os.environ.copy()
    env["PYTHONPATH"] = "src" + (
        os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else ""
    )
    return subprocess.check_output(
        [sys.executable, "-m", "campaignshare_fetcher.cli", *args], env=env
    )


def test_dry_run_outputs_source():
    out = run_cli("--dry-run", "--source", "reddit").decode()
    assert "[dry-run] would fetch from: reddit" in out


def test_default_message_includes_source():
    out = run_cli("--source", "demo").decode()
    assert "campaignshare-fetcher: ready to fetch from demo (stub)" in out
