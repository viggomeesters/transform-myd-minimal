# Transform MYD Minimal - Copilot Agent Guide

## Project Overview

Transform MYD Minimal is a CLI tool for generating column mapping and YAML files from Excel field definitions, specifically designed for SAP data migration workflows. The tool implements advanced field matching algorithms including exact matching, synonym matching, and fuzzy matching using Levenshtein and Jaro-Winkler similarity algorithms.

## Key Features

- **Advanced Field Matching**: Exact, synonym, and fuzzy matching algorithms
- **Multi-File Migration Structure**: Modern YAML-based migration structure
- **Central Mapping Memory**: Reusable mapping rules system
- **Intelligent Field Classification**: Automatic detection of operational vs. business logic fields
- **Backward Compatibility**: Supports legacy command formats

## Project Structure

```
transform-myd-minimal/
├── src/
│   └── transform_myd_minimal/          # Main Python package
│       ├── __init__.py                 # Package initialization
│       ├── __main__.py                 # Module entry point
│       ├── main.py                     # Core orchestration logic
│       ├── cli.py                      # CLI argument parsing
│       ├── config_loader.py            # Configuration management
│       ├── fuzzy.py                    # Fuzzy matching algorithms
│       ├── generator.py                # YAML generation logic
│       └── synonym.py                  # Synonym matching
├── transform-myd-minimal               # Wrapper script
├── configs/                            # Configuration files
├── config/                             # Generated output (legacy)
├── data/                               # Input Excel files
├── migrations/                         # New multi-file structure
└── README.md                          # Main documentation
```

## Core Functionality

### Main Components

1. **Field Matching Engine** (`main.py`):
   - Implements `AdvancedFieldMatcher` class
   - Handles exact, synonym, and fuzzy matching
   - Manages target field deduplication
   - Provides audit logging for transparency

2. **Configuration System** (`config_loader.py`):
   - Loads settings from `configs/config.yaml`
   - Merges CLI arguments with config values
   - Manages input/output directory paths

3. **YAML Generation** (`generator.py`):
   - Creates column mapping YAML files
   - Generates field definitions and value rules
   - Supports both legacy and new migration structures

4. **CLI Interface** (`cli.py`):
   - Modern subcommand structure (`map`)
   - Backward compatibility with legacy format
   - Configurable fuzzy matching parameters

### Key Algorithms

- **Exact Matching**: Normalized field name and description comparison
- **Synonym Matching**: Business term equivalency (NL/EN support)
- **Fuzzy Matching**: Levenshtein distance + Jaro-Winkler similarity
- **Constant Field Detection**: Smart classification of operational fields

## Usage Patterns

### Basic Usage
```bash
./transform-myd-minimal map -object m140 -variant bnka
```

### Advanced Options
```bash
./transform-myd-minimal map -object m140 -variant bnka --fuzzy-threshold 0.8 --max-suggestions 5
```

### Configuration
- Primary config: `configs/config.yaml`
- Central mapping rules: `configs/central_mapping_memory.yaml`
- Input files: `data/02_fields/fields_{object}_{variant}.xlsx`

## Dependencies

- **pandas**: Excel file reading and data manipulation
- **openpyxl**: Excel file format support
- **pyyaml**: YAML file generation and parsing
- **Standard library**: pathlib, typing, dataclasses, etc.

## Development Guidelines

### Code Style
- Uses modern Python features (dataclasses, type hints)
- Follows PEP 8 conventions
- Comprehensive docstrings for all public methods
- Clear separation of concerns between modules

### Testing Strategy
- Manual testing via CLI commands
- Integration testing with sample Excel files
- Console output validation for matching results

### Common Tasks
- Adding new synonym mappings: Edit `synonym.py`
- Adjusting fuzzy algorithms: Modify `fuzzy.py`
- Extending YAML output: Update `generator.py`
- CLI enhancements: Modify `cli.py`

## Business Context

This tool is specifically designed for SAP migration projects where:
- Source systems have field definitions in Excel format
- Target system uses SAP field structures
- Manual mapping would be time-intensive and error-prone
- Audit trails and transparency are required
- Multiple migration objects/variants need processing

The tool significantly reduces manual effort in field mapping while providing confidence scores and audit information for review by subject matter experts.