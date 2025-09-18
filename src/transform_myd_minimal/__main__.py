#!/usr/bin/env python3
"""
Entry point for running transform_myd_minimal as a module.

This allows running the package with: python -m transform_myd_minimal
"""

from .logging_config import setup_logging
from .main import main

if __name__ == "__main__":
    # Initialize logging before running main
    setup_logging()
    main()