# Contributing to Transform MYD Minimal

Thank you for your interest in contributing to Transform MYD Minimal! This document provides guidelines for contributing to the project.

## Development Setup

### Prerequisites
- Python 3.8 or higher
- pip (Python package installer)

### Quick Setup
```bash
# Clone the repository
git clone https://github.com/viggomeesters/transform-myd-minimal.git
cd transform-myd-minimal

# Automated setup (recommended)
python dev_bootstrap.py

# Manual setup
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or
.\.venv\Scripts\Activate.ps1  # Windows PowerShell

pip install -e ".[dev]"
```

### Development Dependencies
- **ruff**: Fast Python linter
- **black**: Code formatter  
- **pytest**: Testing framework
- **mypy**: Static type checker
- **pre-commit**: Git hooks for code quality

## Coding Standards

### Code Style
- **Format**: All code must be formatted with `black`
- **Linting**: Code must pass `ruff` checks
- **Type hints**: Use comprehensive type annotations
- **Docstrings**: Document all public functions and classes

### Commands
```bash
# Format code
black src/ tests/

# Run linter  
ruff check src/ tests/

# Fix auto-fixable issues
ruff check --fix src/ tests/

# Type checking (optional but recommended)
mypy --ignore-missing-imports src/
```

## Testing

### Running Tests
```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src/transform_myd_minimal

# Run specific test
pytest tests/test_cli.py::test_cli_help -v
```

### Test Guidelines
- Write tests for new functionality
- Maintain existing test coverage
- Use descriptive test names
- Test both success and failure cases

## Git Workflow

### Pre-commit Hooks
```bash
# Install pre-commit hooks (included in dev setup)
pre-commit install

# Run hooks manually
pre-commit run --all-files
```

### Commit Messages
Use conventional commits format:
- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation changes
- `test:` Test additions/changes
- `chore:` Maintenance tasks

### Pull Requests
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Ensure tests pass
5. Run linting and formatting
6. Submit a pull request

## Project Structure

```
src/transform_myd_minimal/
├── __init__.py          # Package initialization and version info
├── __main__.py          # Module entry point
├── cli.py               # CLI argument parsing and subcommands
├── main.py              # Core command implementations
├── config_loader.py     # Configuration management
├── enhanced_logging.py  # Rich logging system for F01/F02
├── logging_config.py    # Logging configuration utilities
├── fuzzy.py            # Fuzzy matching algorithms
├── generator.py        # YAML generation logic
├── source_mapping.py   # Mapping logic
├── synonym.py          # Synonym matching utilities
├── parsers.py          # Excel/XML parsing utilities
├── reporting.py        # HTML report generation
└── csv_reporting.py    # CSV data profiling and reporting
```

## Architecture Guidelines

### Error Handling
- Use proper exit codes:
  - `2`: Missing input file
  - `3`: Missing index/headers  
  - `4`: No fields/targets
  - `5`: Would overwrite (without --force)
  - `6`: Invalid validation config
  - `1`: General exception

### Logging
- Use enhanced logging system for F01/F02 commands
- Support both human and JSONL output formats
- Default to TTY-aware output
- Log to `data/99_logging/` by default

### Path Handling
- Always use `pathlib.Path` objects
- Normalize paths with forward slashes for output
- Follow F01-F04 directory structure

## Maintenance Guidelines

### Backward Compatibility  
- Maintain existing CLI interfaces
- Preserve output formats for downstream tools
- Keep configuration file compatibility

### Dependencies
- Minimize new dependencies
- Use standard library when possible
- Document any new requirements

### Performance
- Profile code changes if they affect core operations
- Consider memory usage for large Excel files
- Optimize fuzzy matching algorithms carefully

## Getting Help

- Check existing issues and documentation
- Review the `.copilot/` directory for agent-specific guidance
- Look at `DEVELOPMENT.md` for detailed setup instructions

## License

By contributing, you agree that your contributions will be licensed under the MIT License.