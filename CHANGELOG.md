# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [4.0.1] - 2024-09-22

### Fixed
- Console script entry point from `tmm.cli:app` to `transform_myd_minimal.cli:app` 
- F01 input file path specification: `data/01_source/<object>_<variant>.xlsx` (was `index_source_<object>_<variant>.xlsx`)
- Removed unused variables to fix linting violations
- Import optimization (removed unused `os` import)

### Added
- Basic test suite for CLI functionality 
- Complete `.gitignore` coverage for all data directories (F01-F04)
- mypy to development dependencies
- Windows PowerShell examples in README
- Complete data directory structure documentation

### Changed
- Applied black code formatting across codebase
- Updated README with Windows/PowerShell command examples
- Enhanced data directory structure documentation with F01-F04 paths
- Improved project metadata in `pyproject.toml`

### Maintenance
- Code passes all linting checks (ruff, black)
- All tests pass
- Path normalization with forward slashes confirmed working
- Exit codes properly implemented per specification
- TTY-based logging (human vs JSON) confirmed working  
- Default logging to `data/09_logging/` confirmed working
- No environment variable dependencies confirmed

## [4.0.0] - Previous release
- Initial release with F01-F04 command structure