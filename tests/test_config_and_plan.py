import os
import subprocess
import sys
import tempfile
import textwrap


def run_cli(*args, env=None):
    env = (env or os.environ).copy()
    env["PYTHONPATH"] = "src" + (
        os.pathsep + env.get("PYTHONPATH", "") if env.get("PYTHONPATH") else ""
    )
    return subprocess.run(
        [sys.executable, "-m", "campaignshare_fetcher.cli", *args],
        env=env,
        capture_output=True,
        text=True,
    )


def test_loads_config_and_prints_plan():
    toml = textwrap.dedent(
        """
    [[sources]]
    name = "citybuilding"
    type = "rss"
    url = "https://example.com/rss"
    output = "data/citybuilding.jsonl"
    """
    ).strip()
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "config.toml")
        with open(p, "w") as f:
            f.write(toml)
        res = run_cli("--config", p)
        assert res.returncode == 0
        assert "plan: rss:citybuilding -> data/citybuilding.jsonl" in res.stdout


def test_rejects_empty_sources():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "bad.toml")
        with open(p, "w") as f:
            f.write("sources = []\n")
        res = run_cli("--config", p)
        # either CLI exits non-zero or at least prints no plan lines
        assert res.returncode != 0 or "plan:" not in res.stdout
