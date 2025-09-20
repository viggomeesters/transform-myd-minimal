#!/usr/bin/env python3
"""
CLI entry point using Typer for transform-myd-minimal
"""

import typer
import sys
import os

# Add the transform_myd_minimal package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

app = typer.Typer(
    name="transform-myd-minimal",
    help="Transform MYD Minimal - Advanced Field Matching and YAML Generation",
    add_completion=False,
)

def main():
    """Main entry point that delegates to the existing CLI."""
    try:
        from transform_myd_minimal.logging_config import setup_logging
        from transform_myd_minimal.main import main as legacy_main
        
        # Initialize logging
        setup_logging()
        
        # Call the existing main function
        legacy_main()
    except ImportError as e:
        typer.echo(f"Error importing transform_myd_minimal: {e}")
        typer.echo("Make sure the package is properly installed.")
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"Error: {e}")
        raise typer.Exit(1)

# Create the app callable that setuptools expects
app = main

if __name__ == "__main__":
    main()