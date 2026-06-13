import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_db_inspect_help() -> None:
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "db_inspect.py"), "--help"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "--plan" in result.stdout
