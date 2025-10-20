"""Tests for the web frontend command."""

import subprocess
import sys


def test_frontend_help():
    """Test that frontend command shows help."""
    result = subprocess.run(
        [sys.executable, "-m", "transform_myd_minimal", "frontend", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "--host" in result.stdout
    assert "--port" in result.stdout
    assert "--debug" in result.stdout


def test_frontend_in_main_help():
    """Test that frontend command appears in main help."""
    result = subprocess.run(
        [sys.executable, "-m", "transform_myd_minimal", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "frontend" in result.stdout
    assert "Start the web-based visual workflow designer" in result.stdout
