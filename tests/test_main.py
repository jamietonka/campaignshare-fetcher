import os
import subprocess
import sys


def test_stub_runs_and_prints():
    env = os.environ.copy()
    # ensure the module under src/ is importable by the child interpreter
    env["PYTHONPATH"] = (
        ("src" + os.pathsep + env["PYTHONPATH"])
        if "PYTHONPATH" in env and env["PYTHONPATH"]
        else "src"
    )
    out = subprocess.check_output(
        [sys.executable, "-m", "campaignshare_fetcher.main"],
        env=env,
    )
    assert b"campaignshare-fetcher: ready to fetch (stub)" in out
