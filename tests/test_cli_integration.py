#!/usr/bin/env python3
"""
Tests for CLI HTML reporting flags.
"""

import subprocess
import sys
import tempfile
from pathlib import Path


def run_command(cmd_args, cwd=None):
    """Run a command and return result."""
    if cwd is None:
        cwd = Path(__file__).parent.parent

    result = subprocess.run(
        [sys.executable, "-m", "transform_myd_minimal"] + cmd_args,
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    return result


def test_cli_html_flags():
    """Test that HTML flags are present in all commands."""
    commands = ["index_source", "index_target", "map", "transform"]

    for cmd in commands:
        result = run_command([cmd, "--help"])
        assert result.returncode == 0, f"Help failed for {cmd}"
        assert "--no-html" in result.stdout, f"--no-html flag missing in {cmd}"
        assert "--html-dir" in result.stdout, f"--html-dir flag missing in {cmd}"
        print(f"✓ {cmd} command has HTML flags")


def test_no_html_flag():
    """Test that --no-html flag prevents HTML generation."""
    # This test would need actual data files to work properly
    # For now, just test that the flag is accepted
    result = run_command(
        ["index_source", "--object", "test", "--variant", "test", "--no-html"]
    )
    # Command will fail due to missing files, but should not fail due to unknown flag
    assert (
        "--no-html" not in result.stderr
        or "unrecognized arguments" not in result.stderr
    )


def test_html_dir_flag():
    """Test that --html-dir flag is accepted."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = run_command(
            [
                "index_source",
                "--object",
                "test",
                "--variant",
                "test",
                "--html-dir",
                tmpdir,
            ]
        )
        # Command will fail due to missing files, but should not fail due to unknown flag
        assert (
            "--html-dir" not in result.stderr
            or "unrecognized arguments" not in result.stderr
        )


def test_command_completeness():
    """Test that all four main commands are available."""
    result = run_command(["--help"])
    assert result.returncode == 0

    commands = ["index_source", "index_target", "map", "transform"]
    for cmd in commands:
        assert cmd in result.stdout, f"Command {cmd} not found in help"

    print("✓ All four F01-F04 commands are available")


if __name__ == "__main__":
    print("Running CLI integration tests...")

    test_cli_html_flags()
    print("✓ All commands have HTML flags")

    test_no_html_flag()
    print("✓ --no-html flag test passed")

    test_html_dir_flag()
    print("✓ --html-dir flag test passed")

    test_command_completeness()
    print("✓ Command completeness test passed")

    print("All CLI integration tests passed!")
