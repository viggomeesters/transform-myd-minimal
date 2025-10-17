# Development Setup Guide

## Prerequisites

- Python 3.11 or higher (project requires >=3.11)
- pip (Python package installer)

## Quick Setup

### 1. Clone the Repository
```bash
git clone https://github.com/viggomeesters/transform-myd-minimal.git
cd transform-myd-minimal
```

### 2. Install Dependencies

Preferred (Windows PowerShell):

```powershell
# Create full dev environment (.venv) and install ALL dependencies
py -3.12 dev_bootstrap.py

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Verify CLI
transform-myd-minimal --help
py -3.12 -m transform_myd_minimal --help
```

Manual alternative:

```powershell
# Create and activate venv
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1

# Upgrade packaging tools and install runtime deps
py -3.12 -m pip install -U pip setuptools wheel
py -3.12 -m pip install -r requirements.txt

# Optional: dev dependencies + editable install
py -3.12 -m pip install -e ".[dev]"
```

### 3. Verify Installation
```powershell
# Windows PowerShell
transform-myd-minimal --help
py -3.12 -m transform_myd_minimal --help
```

```bash
# Linux/macOS (alternative)
./transform-myd-minimal --help
python3 -m transform_myd_minimal --help
```

## Project Structure Overview

```
transform-myd-minimal/
├── .copilot/                           # Copilot agent documentation
│   ├── README.md                       # Project overview for agents
│   └── instructions.md                 # Development instructions for agents
├── src/
│   └── transform_myd_minimal/          # Main Python package
│       ├── __init__.py                 # Package initialization (version info)
│       ├── __main__.py                 # Module entry point
│       ├── main.py                     # Core orchestration and matching logic
│       ├── cli.py                      # CLI argument parsing and subcommands
│       ├── config_loader.py            # Configuration management
│       ├── enhanced_logging.py         # Rich logging system for F01/F02
│       ├── logging_config.py           # Logging configuration utilities
│       ├── fuzzy.py                    # Fuzzy matching algorithms
│       ├── generator.py                # YAML generation logic
│       ├── source_mapping.py           # Mapping logic
│       ├── synonym.py                  # Synonym matching utilities
│       ├── parsers.py                  # Excel/XML parsing utilities
│       ├── reporting.py               # HTML report generation
│       └── csv_reporting.py           # CSV data profiling and reporting
├── transform-myd-minimal               # Wrapper script for easy execution
├── config/                             # Configuration directory
│   ├── config.yaml                     # Application settings (if exists)
│   └── central_mapping_memory.yaml     # Central mapping rules (if exists)
├── data/                               # Input data and outputs
│   ├── 01_source/                      # F01 inputs (source XLSX files)
│   ├── 02_target/                      # F02 inputs (target XML files)
│   ├── 03_index_source/                # F01 HTML/JSON reports
│   ├── 04_index_target/                # F02 HTML/JSON reports
│   ├── 05_map/                         # F03 HTML/JSON reports
│   ├── 06_template/                    # F04 CSV templates
│   ├── 07_raw/                         # F04 raw data inputs
│   ├── 08_raw_validation/              # F04 validation outputs
│   ├── 09_rejected/                    # F04 rejected records
│   ├── 10_transformed/                 # F04 final CSV outputs
│   ├── 11_transformed_validation/      # F04 post-transform validation
│   └── 99_logging/                     # All log files
├── migrations/                         # Generated YAML structures
│   └── {object}/                       # Per object directory
│       └── {variant}/                  # Per variant directory
│           ├── index_source.yaml       # F01 output
│           ├── index_target.yaml       # F02 output
│           └── mapping.yaml            # F03 output
├── requirements.txt                    # Python dependencies
├── pyproject.toml                      # Modern Python project configuration
└── README.md                          # Main project documentation
```

## Running the Tool

### Step-by-Step Workflow (v4.1)

Transform MYD Minimal uses a 4-step pipeline:

```powershell
# Windows PowerShell
py -3.12 -m transform_myd_minimal index_source  --object m140 --variant bnka
py -3.12 -m transform_myd_minimal index_target  --object m140 --variant bnka
py -3.12 -m transform_myd_minimal map           --object m140 --variant bnka
py -3.12 -m transform_myd_minimal transform     --object m140 --variant bnka
```

```bash
# Linux/macOS (alternative)
./transform-myd-minimal index_source  --object m140 --variant bnka
./transform-myd-minimal index_target  --object m140 --variant bnka
./transform-myd-minimal map           --object m140 --variant bnka
./transform-myd-minimal transform     --object m140 --variant bnka
```

### View Available Options
```powershell
# Windows PowerShell
py -3.12 -m transform_myd_minimal --help
py -3.12 -m transform_myd_minimal index_source  --help
py -3.12 -m transform_myd_minimal index_target  --help
py -3.12 -m transform_myd_minimal map           --help
py -3.12 -m transform_myd_minimal transform     --help
```

```bash
# Linux/macOS (alternative)
./transform-myd-minimal --help
./transform-myd-minimal index_source  --help
./transform-myd-minimal index_target  --help
./transform-myd-minimal map           --help
./transform-myd-minimal transform     --help
```

### Advanced Options
```powershell
# Windows PowerShell examples
py -3.12 -m transform_myd_minimal map          --object m140 --variant bnka --fuzzy-threshold 0.8
py -3.12 -m transform_myd_minimal map          --object m140 --variant bnka --disable-fuzzy
py -3.12 -m transform_myd_minimal map          --object m140 --variant bnka --max-suggestions 10
py -3.12 -m transform_myd_minimal index_source --object m140 --variant bnka --no-html
py -3.12 -m transform_myd_minimal index_source --object m140 --variant bnka --force
py -3.12 -m transform_myd_minimal index_target --object m140 --variant bnka --quiet --log-file my_log.jsonl
```

```bash
# Linux/macOS (alternative)
./transform-myd-minimal map          --object m140 --variant bnka --fuzzy-threshold 0.8
./transform-myd-minimal map          --object m140 --variant bnka --disable-fuzzy
./transform-myd-minimal map          --object m140 --variant bnka --max-suggestions 10
./transform-myd-minimal index_source --object m140 --variant bnka --no-html
./transform-myd-minimal index_source --object m140 --variant bnka --force
./transform-myd-minimal index_target --object m140 --variant bnka --quiet --log-file my_log.jsonl
```

### Input Requirements

The tool expects the following file structure:

**F01 (index_source):**
- Path: `data/01_source/{object}_{variant}.xlsx`
- Content: Excel file with source headers

**F02 (index_target):**
- Path: `data/02_target/{object}_{variant}.xml`  
- Fallback: `data/02_target/{object}_{variant}.xlsx`
- Content: Target field definitions

**F04 (transform):**
- Path: `data/07_raw/{object}_{variant}.xlsx` - Raw data to transform
- Templates: `data/06_template/S_{VARIANT}#*.csv` - CSV templates

## Configuration

### Application Settings (`config/config.yaml`)
```yaml
# Fuzzy matching configuration
fuzzy_threshold: 0.6        # Matching threshold (0.0-1.0)
max_suggestions: 3          # Maximum suggestions to show
disable_fuzzy: false        # Whether to disable fuzzy matching

# Directory configuration  
input_dir: "data/01_source"   # F01 input directory for source Excel files
output_dir: "migrations"      # Output directory for generated YAML files
```

### Central Mapping Memory (`config/central_mapping_memory.yaml`)
Defines reusable mapping rules that apply across multiple objects/variants:
- Global skip fields (fields to ignore)
- Global manual mappings (explicit field mappings)
- Table-specific overrides

## Development Workflow

### Making Changes

1. **Modify source code** in `src/transform_myd_minimal/`
2. **Test changes** using the CLI with sample data
3. **Verify outputs** by checking generated YAML files
4. **Update documentation** if adding new features

### Common Development Tasks

#### Adding New Fuzzy Matching Algorithms
1. Add static method to `FuzzyMatcher` class in `fuzzy.py`
2. Update `AdvancedFieldMatcher` in `main.py` to use the new algorithm
3. Add configuration options in `config_loader.py`
4. Update CLI arguments in `cli.py`

#### Extending YAML Output Format
1. Modify generator functions in `generator.py`
2. Update data structures if needed
3. Test with sample data to ensure valid YAML

#### Adding New CLI Commands
1. Add subparser in `cli.py` `setup_cli()` function
2. Create handler function in appropriate module
3. Wire up in `main()` orchestration function

### Testing

Since no formal test suite currently exists:

1. **Manual CLI testing**:
   ```bash
   ./transform-myd-minimal --help
   ./transform-myd-minimal map --help
   ```

2. **Integration testing** (if sample data available):
   ```bash
   ./transform-myd-minimal map --object m140 --variant bnka
   ```

3. **Output validation**:
   - Check console output for expected statistics
   - Verify YAML files are generated correctly
   - Ensure both legacy and new structures are created

### Code Style Guidelines

- **Type hints**: Use comprehensive type annotations
- **Docstrings**: Document all public functions and classes
- **Error handling**: Provide clear, contextual error messages
- **Console output**: Use structured formatting for user feedback
- **Backward compatibility**: Maintain existing CLI interfaces

## Troubleshooting

### Common Issues

1. **ModuleNotFoundError**: Ensure dependencies are installed (`pip install -r requirements.txt`)
2. **FileNotFoundError**: Check that input Excel files exist in the expected location
3. **Permission errors**: Ensure write permissions for output directories
4. **Import errors**: Verify Python path includes the `src` directory

### Debugging Tips

- Use `--max-suggestions 10` to see more matching candidates
- Lower `--fuzzy-threshold` to understand why matches might be missed
- Check console output for detailed matching statistics
- Review generated YAML comments for audit information
- Use `--disable-fuzzy` to isolate exact matching issues

## Contributing

When making contributions:

1. Preserve backward compatibility for existing CLI interfaces
2. Maintain the Excel input file format expectations
3. Keep existing YAML output structures for legacy mode
4. Update documentation for new features
5. Test thoroughly with sample data before submitting changes
