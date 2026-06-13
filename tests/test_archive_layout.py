"""Phase 0 archive layout checks."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_legacy_feature_docs_archived() -> None:
    assert not (REPO_ROOT / "docs" / "features").exists()
    assert (REPO_ROOT / "archive" / "docs" / "features").is_dir()


def test_superpowers_docs_remain() -> None:
    assert (REPO_ROOT / "docs" / "superpowers" / "specs").is_dir()


def test_legacy_app_trees_removed() -> None:
    assert not (REPO_ROOT / "backend").exists()
    assert not (REPO_ROOT / "frontend").exists()
    assert not (REPO_ROOT / ".devcontainer").exists()
