# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Automated runtime dependency verification in bootstrap**:
  - `dev_bootstrap.py` now verifies that all runtime dependencies (typer, pandas, openpyxl, PyYAML, lxml, python-dateutil, rapidfuzz, rich) are importable after installation
  - Automatically installs any missing dependencies to prevent `ModuleNotFoundError` at runtime
  - Provides clear status feedback during bootstrap for each dependency

### Changed
- **requirements.txt synchronized with pyproject.toml**:
  - Now includes all runtime dependencies from `[project.dependencies]`
  - Prevents missing module errors when installing via `pip install -r requirements.txt`
- **Documentation updates for Windows/PowerShell users**:
  - Added quick start examples using `py -3.12` launcher in README.md
  - Updated DEVELOPMENT.md with Windows venv setup instructions
  - Updated USAGE.md with Windows command examples
  - Added Quick Onboarding section to QA_SETUP_SUMMARY.md

### Fixed
- Missing runtime dependency `rich` now guaranteed to be installed via bootstrap
- Windows PowerShell users no longer need to manually troubleshoot missing dependencies

## [4.1.0] - 2024-09-23

### Added
- **Self-contained HTML reports for ALL F01–F04 steps** with interactive features:
  - KPI cards, bar charts, sortable/searchable tables
  - Client-side CSV export functionality  
  - Embedded JSON data in `<script id="data">` tags
  - Responsive design with inline CSS/JS (no external dependencies)
- **HTML reporting CLI flags** for all commands:
  - `--no-html` to skip HTML generation (JSON still generated)
  - `--html-dir PATH` to customize report output directory
- **Step-specific HTML report content**:
  - F01: Headers analysis with duplicates detection
  - F02: Target fields with group distribution charts
  - F03: Mapping results with confidence scores and audit items
  - F04: Dual reports for RAW validation + POST-transform validation
- **Report locations**:
  - F01-F03: `data/03_index_source/`, `data/04_index_target/`, `data/05_map/`
  - F04 RAW: `data/08_raw_validation/`
  - F04 POST: `data/11_transformed_validation/`
- **Comprehensive test suite** for HTML reporting functionality
- **Enhanced documentation** in README.md and USAGE.md with HTML reporting examples

### Changed
- HTML reporting enabled by default (can be disabled with `--no-html`)
- Console output includes `report: <path>` for generated HTML files  
- All paths in console output use forward slashes for cross-platform compatibility
- JSON summaries now include enhanced metadata for HTML rendering

### Technical
- New module: `src/transform_myd_minimal/reporting.py` with HTML generation utilities
- `write_html_report()` function for self-contained HTML with embedded JSON
- `ensure_json_serializable()` utility for safe JSON embedding
- Enhanced CLI argument parsing for HTML flags across all commands
- XSS protection via JSON escaping (`</script>` → `</scr"+"ipt>`)

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
- Default logging to `data/99_logging/` confirmed working
- No environment variable dependencies confirmed

## [4.0.0] - Previous release
- Initial release with F01-F04 command structure
