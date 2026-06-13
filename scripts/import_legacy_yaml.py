#!/usr/bin/env python3
"""Import legacy config.yml into SQLite. Full implementation: Phase 4."""

from __future__ import annotations

import argparse
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("yaml_path", help="Path to legacy config.yml")
    _ = parser.parse_args()
    print("import_legacy_yaml.py is not implemented until Phase 4.", file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
