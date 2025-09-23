#!/usr/bin/env python3
"""
Basic tests for transform-myd-minimal CLI functionality.
"""

import subprocess
import sys
from pathlib import Path


def test_cli_help():
    """Test that the CLI help command works."""
    result = subprocess.run(
        [sys.executable, "-m", "transform_myd_minimal", "--help"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    assert result.returncode == 0
    assert "Transform MYD Minimal" in result.stdout
    assert "index_source" in result.stdout
    assert "index_target" in result.stdout
    assert "map" in result.stdout
    assert "transform" in result.stdout


def test_index_source_help():
    """Test that the index_source help command works."""
    result = subprocess.run(
        [sys.executable, "-m", "transform_myd_minimal", "index_source", "--help"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    assert result.returncode == 0
    assert "index_source" in result.stdout


def test_index_target_help():
    """Test that the index_target help command works."""
    result = subprocess.run(
        [sys.executable, "-m", "transform_myd_minimal", "index_target", "--help"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    assert result.returncode == 0
    assert "index_target" in result.stdout


def test_map_help():
    """Test that the map help command works."""
    result = subprocess.run(
        [sys.executable, "-m", "transform_myd_minimal", "map", "--help"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    assert result.returncode == 0
    assert "map" in result.stdout


def test_transform_help():
    """Test that the transform help command works."""
    result = subprocess.run(
        [sys.executable, "-m", "transform_myd_minimal", "transform", "--help"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    assert result.returncode == 0
    assert "transform" in result.stdout


def test_missing_command():
    """Test that missing command shows help and exits with code 1."""
    result = subprocess.run(
        [sys.executable, "-m", "transform_myd_minimal"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    assert result.returncode == 1
    assert "Transform MYD Minimal" in result.stdout or "Transform MYD Minimal" in result.stderr
