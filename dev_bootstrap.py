#!/usr/bin/env python3
"""
Cross-platform development environment bootstrap script for transform-myd-minimal.

Creates a virtual environment, installs dependencies, sets up pre-commit hooks,
and prepares a complete development environment with one command.

Usage:
    python dev_bootstrap.py [--recreate] [--python 3.11|3.12|3.13] [--extras dev] [--no-precommit] [--no-editable] [--uv]
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path
import shutil
import platform

# Rich imports with fallback
try:
    from rich.console import Console
    from rich.progress import Progress
    from rich.panel import Panel
    from rich.text import Text

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

    class Console:
        def print(self, *args, **kwargs):
            print(*args)

    class Progress:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def add_task(self, *args, **kwargs):
            return 0

        def update(self, *args, **kwargs):
            pass


console = Console()


def sh(cmd: list, env=None, cwd=None, check=True):
    """Execute shell command with error handling."""
    try:
        result = subprocess.run(
            cmd, check=check, capture_output=True, text=True, env=env, cwd=cwd
        )
        return result
    except subprocess.CalledProcessError as e:
        console.print(
            f"[red]✗[/red] Command failed: {' '.join(cmd)}"
            if RICH_AVAILABLE
            else f"✗ Command failed: {' '.join(cmd)}"
        )
        console.print(
            f"[red]Error:[/red] {e.stderr}" if RICH_AVAILABLE else f"Error: {e.stderr}"
        )
        raise
    except FileNotFoundError:
        console.print(
            f"[red]✗[/red] Command not found: {cmd[0]}"
            if RICH_AVAILABLE
            else f"✗ Command not found: {cmd[0]}"
        )
        raise


def print_header():
    """Print bootstrap header information."""
    if RICH_AVAILABLE:
        header = Panel.fit(
            "[bold blue]Transform MYD Minimal[/bold blue]\n"
            "[dim]Development Environment Bootstrap[/dim]",
            border_style="blue",
        )
        console.print(header)
    else:
        console.print("=" * 50)
        console.print("Transform MYD Minimal")
        console.print("Development Environment Bootstrap")
        console.print("=" * 50)


def print_success(msg: str):
    """Print success message."""
    console.print(f"[green]✓[/green] {msg}" if RICH_AVAILABLE else f"✓ {msg}")


def print_warning(msg: str):
    """Print warning message."""
    console.print(f"[yellow]⚠[/yellow] {msg}" if RICH_AVAILABLE else f"⚠ {msg}")


def print_error(msg: str):
    """Print error message."""
    console.print(f"[red]✗[/red] {msg}" if RICH_AVAILABLE else f"✗ {msg}")


def print_info(msg: str):
    """Print info message."""
    console.print(f"[cyan]ℹ[/cyan] {msg}" if RICH_AVAILABLE else f"ℹ {msg}")


def normalize_path(path: Path) -> str:
    """Normalize path for display (forward slashes)."""
    return str(path).replace("\\", "/")


def detect_uv() -> bool:
    """Check if uv is available."""
    try:
        sh(["uv", "--version"], check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def get_python_executable(python_version: str = None) -> str:
    """Get the appropriate Python executable."""
    if python_version:
        if platform.system() == "Windows":
            # Try py launcher first
            try:
                result = sh(["py", f"-{python_version}", "--version"], check=True)
                return f"py -{python_version}"
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass

        # Try python3.x
        try:
            python_cmd = f"python{python_version}"
            sh([python_cmd, "--version"], check=True)
            return python_cmd
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

        # Try python3 with specific version check
        try:
            result = sh(["python3", "--version"], check=True)
            if python_version in result.stdout:
                return "python3"
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

        raise RuntimeError(f"Python {python_version} not found")

    # Default python
    if platform.system() == "Windows":
        try:
            sh(["python", "--version"], check=True)
            return "python"
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        raise RuntimeError("No Python interpreter found on Windows")
    else:
        for cmd in ["python3", "python"]:
            try:
                sh([cmd, "--version"], check=True)
                return cmd
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue
        raise RuntimeError("No Python interpreter found")


def check_existing_venv(venv_path: Path) -> bool:
    """Check if we're in a virtual environment or if .venv exists."""
    in_venv = hasattr(sys, "real_prefix") or (
        hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
    )

    if in_venv:
        print_warning(f"Already inside a virtual environment: {sys.prefix}")
        return True

    if venv_path.exists():
        print_warning(
            f"Virtual environment already exists: {normalize_path(venv_path)}"
        )
        return True

    return False


def create_venv(venv_path: Path, python_cmd: str, recreate: bool = False):
    """Create virtual environment."""
    if venv_path.exists() and recreate:
        print_info(
            f"Removing existing virtual environment: {normalize_path(venv_path)}"
        )
        shutil.rmtree(venv_path)

    if not venv_path.exists():
        print_info(f"Creating virtual environment with {python_cmd}...")

        if python_cmd.startswith("py -"):
            # Windows py launcher
            version = python_cmd.split("-")[1]
            sh(["py", f"-{version}", "-m", "venv", str(venv_path)])
        else:
            sh([python_cmd, "-m", "venv", str(venv_path)])

        print_success(f"Created virtual environment: {normalize_path(venv_path)}")


def get_venv_python(venv_path: Path) -> str:
    """Get the Python executable from virtual environment."""
    if platform.system() == "Windows":
        return str(venv_path / "Scripts" / "python.exe")
    else:
        return str(venv_path / "bin" / "python")


def get_venv_pip(venv_path: Path) -> str:
    """Get the pip executable from virtual environment."""
    if platform.system() == "Windows":
        return str(venv_path / "Scripts" / "pip.exe")
    else:
        return str(venv_path / "bin" / "pip")


def upgrade_pip(venv_python: str, use_uv: bool = False):
    """Upgrade pip, setuptools, and wheel."""
    print_info("Upgrading pip, setuptools, and wheel...")

    if use_uv:
        # uv doesn't need pip upgrades, it handles this internally
        print_success("Using uv (pip upgrade not needed)")
    else:
        try:
            sh(
                [
                    venv_python,
                    "-m",
                    "pip",
                    "install",
                    "--upgrade",
                    "pip",
                    "setuptools",
                    "wheel",
                ]
            )
            print_success("Upgraded pip, setuptools, and wheel")
        except subprocess.CalledProcessError:
            print_warning(
                "Pip upgrade failed (network timeout), continuing with existing pip version"
            )


def install_project_manual(venv_path: Path, extras: str = "dev"):
    """Manual installation approach when pip install -e . fails."""
    venv_python = get_venv_python(venv_path)

    print_info("Installing dependencies manually...")

    # Core dependencies
    core_deps = [
        "typer>=0.12",
        "pandas>=2.2",
        "openpyxl>=3.1",
        "PyYAML>=6.0",
        "lxml>=5.2",
        "python-dateutil>=2.9",
        "rapidfuzz>=3.9",
        "rich>=13.7",
    ]

    dev_deps = [
        "ruff>=0.6",
        "black>=24.8",
        "pytest>=8.3",
        "pytest-cov>=5.0",
        "pre-commit>=3.8",
    ]

    # Install core dependencies
    for dep in core_deps:
        try:
            sh([venv_python, "-m", "pip", "install", "--timeout", "120", dep])
        except subprocess.CalledProcessError:
            print_warning(f"Failed to install {dep}, continuing...")

    # Install dev dependencies if requested
    if "dev" in extras:
        for dep in dev_deps:
            try:
                sh([venv_python, "-m", "pip", "install", "--timeout", "120", dep])
            except subprocess.CalledProcessError:
                print_warning(f"Failed to install {dep}, continuing...")

    # Set up package path manually (equivalent to -e install)
    site_packages = venv_path / "lib" / "python3.12" / "site-packages"
    if platform.system() == "Windows":
        site_packages = venv_path / "Lib" / "site-packages"

    # Find the actual python version directory
    python_dirs = (
        list((venv_path / "lib").glob("python*"))
        if (venv_path / "lib").exists()
        else []
    )
    if not python_dirs and platform.system() != "Windows":
        python_dirs = (
            list((venv_path / "Lib").glob("python*"))
            if (venv_path / "Lib").exists()
            else []
        )

    if python_dirs:
        site_packages = python_dirs[0] / "site-packages"

    site_packages.mkdir(parents=True, exist_ok=True)
    pth_file = site_packages / "transform-myd-minimal.pth"
    pth_file.write_text(str(Path.cwd() / "src"))

    # Create CLI executable
    create_cli_executable(venv_path)

    print_success("Manual installation completed")


def create_cli_executable(venv_path: Path):
    """Create CLI executable script."""
    if platform.system() == "Windows":
        cli_path = venv_path / "Scripts" / "transform-myd-minimal.exe"
    else:
        cli_path = venv_path / "bin" / "transform-myd-minimal"

    cli_content = f"""#!/usr/bin/env python
\"\"\"
Entry point for transform-myd-minimal CLI
\"\"\"
import sys
import os

# Add the project src to path
sys.path.insert(0, '{Path.cwd() / "src"}')

if __name__ == '__main__':
    from tmm.cli import main
    main()
"""

    cli_path.write_text(cli_content)
    if platform.system() != "Windows":
        cli_path.chmod(0o755)


def install_project(
    venv_path: Path, extras: str = "dev", editable: bool = True, use_uv: bool = False
):
    """Install project with dependencies."""
    venv_python = get_venv_python(venv_path)

    print_info(f"Installing project with extras: {extras}")

    try:
        if use_uv:
            if editable:
                cmd = ["uv", "pip", "install", "-e", f".[{extras}]"]
            else:
                cmd = ["uv", "pip", "install", ".", f".[{extras}]"]
        else:
            if editable:
                cmd = [venv_python, "-m", "pip", "install", "-e", f".[{extras}]"]
            else:
                cmd = [venv_python, "-m", "pip", "install", ".", f".[{extras}]"]

        # Set environment to use the virtual environment
        env = os.environ.copy()
        if use_uv:
            env["VIRTUAL_ENV"] = str(venv_path)
            env["PATH"] = (
                f"{venv_path / 'bin' if platform.system() != 'Windows' else venv_path / 'Scripts'}{os.pathsep}{env['PATH']}"
            )

        sh(cmd, env=env)
        print_success(f"Installed project with {extras} dependencies")
    except subprocess.CalledProcessError:
        print_warning("Standard installation failed, trying manual approach...")
        install_project_manual(venv_path, extras)


def install_precommit_hooks(venv_path: Path, skip_precommit: bool = False):
    """Install pre-commit hooks."""
    if skip_precommit:
        print_info("Skipping pre-commit hook installation")
        return

    venv_python = get_venv_python(venv_path)

    # Check if pre-commit config exists
    if not Path(".pre-commit-config.yaml").exists():
        print_warning("No .pre-commit-config.yaml found, skipping pre-commit setup")
        return

    print_info("Installing pre-commit hooks...")
    try:
        sh([venv_python, "-m", "pre_commit", "install"])
        print_success("Installed pre-commit hooks")
    except subprocess.CalledProcessError:
        print_warning(
            "Failed to install pre-commit hooks. Run manually: pre-commit install"
        )


def run_smoke_tests(venv_path: Path):
    """Run smoke tests to verify installation."""
    venv_python = get_venv_python(venv_path)

    print_info("Running smoke tests...")

    # Test 1: Import package
    try:
        sh([venv_python, "-c", "import tmm, sys; print('Package import: OK')"])
        print_success("Package import test passed")
    except subprocess.CalledProcessError:
        print_error("Package import test failed")
        return False

    # Test 2: CLI help
    try:
        sh([venv_python, "-m", "pip", "show", "transform-myd-minimal"])
        if platform.system() == "Windows":
            cli_cmd = str(venv_path / "Scripts" / "transform-myd-minimal.exe")
        else:
            cli_cmd = str(venv_path / "bin" / "transform-myd-minimal")

        if Path(cli_cmd).exists():
            sh([cli_cmd, "--help"])
            print_success("CLI help test passed")
        else:
            print_warning("CLI executable not found, but package is installed")
    except subprocess.CalledProcessError:
        print_warning("CLI help test failed")

    return True


def print_activation_instructions(venv_path: Path):
    """Print virtual environment activation instructions."""
    norm_path = normalize_path(venv_path)

    if RICH_AVAILABLE:
        activation_text = Text()
        activation_text.append(
            "Virtual environment created successfully!\n\n", style="bold green"
        )
        activation_text.append("To activate the environment:\n\n", style="bold")

        if platform.system() == "Windows":
            activation_text.append("PowerShell:\n", style="bold cyan")
            activation_text.append(f"  .\\{norm_path}\\Scripts\\Activate.ps1\n\n")
            activation_text.append("Command Prompt:\n", style="bold cyan")
            activation_text.append(f"  .\\{norm_path}\\Scripts\\activate.bat\n\n")
        else:
            activation_text.append("Bash/Zsh/Fish:\n", style="bold cyan")
            activation_text.append(f"  source {norm_path}/bin/activate\n\n")

        activation_text.append("To verify installation:\n", style="bold")
        activation_text.append("  transform-myd-minimal --help\n")
        activation_text.append("  pre-commit run --all-files\n")
        activation_text.append("  pytest -q\n")

        panel = Panel(activation_text, title="🎉 Setup Complete", border_style="green")
        console.print(panel)
    else:
        console.print("\n" + "=" * 50)
        console.print("🎉 Setup Complete!")
        console.print("=" * 50)
        console.print("Virtual environment created successfully!")
        console.print("\nTo activate the environment:")

        if platform.system() == "Windows":
            console.print(f"PowerShell:       .\\{norm_path}\\Scripts\\Activate.ps1")
            console.print(f"Command Prompt:   .\\{norm_path}\\Scripts\\activate.bat")
        else:
            console.print(f"Bash/Zsh/Fish:    source {norm_path}/bin/activate")

        console.print("\nTo verify installation:")
        console.print("  transform-myd-minimal --help")
        console.print("  pre-commit run --all-files")
        console.print("  pytest -q")


def write_bootstrap_log(venv_path: Path, start_time: float, success: bool):
    """Write bootstrap log with versions and status."""
    venv_python = get_venv_python(venv_path)
    elapsed = time.perf_counter() - start_time

    log_content = [
        f"Bootstrap completed at: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"Elapsed time: {elapsed:.2f} seconds",
        f"Success: {success}",
        f"Virtual environment: {normalize_path(venv_path)}",
        f"Platform: {platform.system()} {platform.release()}",
        "",
    ]

    if success:
        try:
            # Get Python version
            result = sh([venv_python, "--version"], check=True)
            log_content.append(f"Python version: {result.stdout.strip()}")

            # Get package version
            result = sh(
                [venv_python, "-m", "pip", "show", "transform-myd-minimal"], check=True
            )
            for line in result.stdout.split("\n"):
                if line.startswith("Version:"):
                    log_content.append(
                        f"Package version: {line.split(':', 1)[1].strip()}"
                    )
                    break
        except subprocess.CalledProcessError:
            log_content.append("Package version: Unknown")

    with open(".bootstrap.log", "w") as f:
        f.write("\n".join(log_content))

    print_info("Bootstrap log written to: .bootstrap.log")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Bootstrap development environment for transform-myd-minimal",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python dev_bootstrap.py                    # Use current Python, dev extras
  python dev_bootstrap.py --python 3.11     # Use Python 3.11
  python dev_bootstrap.py --recreate         # Recreate existing venv
  python dev_bootstrap.py --uv               # Use uv if available
  python dev_bootstrap.py --no-precommit     # Skip pre-commit setup
        """,
    )

    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Remove and recreate existing virtual environment",
    )

    parser.add_argument(
        "--python",
        choices=["3.11", "3.12", "3.13"],
        help="Python version to use (default: current interpreter)",
    )

    parser.add_argument(
        "--extras", default="dev", help="Package extras to install (default: dev)"
    )

    parser.add_argument(
        "--no-precommit", action="store_true", help="Skip pre-commit hook installation"
    )

    parser.add_argument(
        "--no-editable",
        action="store_true",
        help="Install package in non-editable mode",
    )

    parser.add_argument(
        "--uv", action="store_true", help="Use uv for package installation if available"
    )

    return parser.parse_args()


def main():
    """Main bootstrap function."""
    args = parse_args()
    start_time = time.perf_counter()

    # Print header
    print_header()

    # Configuration
    venv_path = Path(".venv")
    use_uv = args.uv and detect_uv()

    if use_uv:
        print_info("Using uv for package management")

    try:
        # Check Python
        python_cmd = get_python_executable(args.python)
        print_info(f"Using Python: {python_cmd}")

        # Check existing venv
        if check_existing_venv(venv_path) and not args.recreate:
            print_info("Reusing existing virtual environment")
        else:
            create_venv(venv_path, python_cmd, args.recreate)

        # Upgrade pip
        venv_python = get_venv_python(venv_path)
        upgrade_pip(venv_python, use_uv)

        # Install project
        install_project(venv_path, args.extras, not args.no_editable, use_uv)

        # Setup pre-commit
        install_precommit_hooks(venv_path, args.no_precommit)

        # Run smoke tests
        success = run_smoke_tests(venv_path)

        # Print activation instructions
        print_activation_instructions(venv_path)

        # Write log
        write_bootstrap_log(venv_path, start_time, success)

        if not success:
            print_warning("Some tests failed, but environment should be usable")

        return 0

    except Exception as e:
        print_error(f"Bootstrap failed: {e}")
        write_bootstrap_log(venv_path, start_time, False)
        return 1


if __name__ == "__main__":
    sys.exit(main())
