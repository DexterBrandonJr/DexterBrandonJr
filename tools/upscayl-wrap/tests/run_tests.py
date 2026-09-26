#!/usr/bin/env python3
"""Run every test. No third-party test runner required.

    python3 tests/run_tests.py
    python3 tests/run_tests.py -v
"""

from __future__ import annotations

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(HERE)
for path in (PROJECT_DIR, HERE):
    if path not in sys.path:
        sys.path.insert(0, path)


def main() -> int:
    verbosity = 2 if "-v" in sys.argv else 1
    suite = unittest.defaultTestLoader.discover(HERE, pattern="test_*.py", top_level_dir=HERE)
    result = unittest.TextTestRunner(verbosity=verbosity).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
