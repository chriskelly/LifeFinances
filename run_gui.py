#!/usr/bin/env python3
"""
LifeFinances Qt GUI Entry Point.

This script launches the PyQt6-based desktop application for LifeFinances.
It sets up the environment to prevent Flask initialization and starts the
Qt application.

Usage:
    python run_gui.py
"""

import os
import sys
from pathlib import Path

# Set environment variable to skip Flask initialization
os.environ["SKIP_FLASK_INIT"] = "1"

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from PyQt6.QtWidgets import QApplication
from qt_gui.windows.main_window import MainWindow


def main() -> int:
    """
    Launch the LifeFinances Qt GUI application.

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    app = QApplication(sys.argv)
    app.setApplicationName("LifeFinances")
    app.setOrganizationName("LifeFinances")

    # Create and show main window
    main_window = MainWindow()
    main_window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
