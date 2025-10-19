# Directory Structure

This document describes the complete directory structure of the Transform MYD Minimal project.

## Overview

The project follows a numbered directory structure for data processing stages, ensuring clear separation of concerns and easy tracking of data flow through the transformation pipeline.

## Root Structure

```
transform-myd-minimal/
├── .github/              # GitHub Actions workflows and configuration
├── config/               # Configuration files
├── data/                 # Data directories (F01-F04 pipeline stages)
├── docs/                 # Documentation
├── migrations/           # Generated YAML migration files
├── scripts/              # Utility scripts
├── src/                  # Source code (transform_myd_minimal package)
├── tests/                # Test suite
├── .gitignore            # Git ignore patterns
├── pyproject.toml        # Project configuration and dependencies
├── requirements.txt      # Runtime dependencies
└── README.md             # Main documentation
```

## Data Directory Structure

All data directories follow a numbered convention for pipeline stages:

### Input Directories

| Directory | Purpose | Tracked in Git | Description |
|-----------|---------|----------------|-------------|
| `data/01_source/` | Source Excel files | Test files only | Excel files containing source system headers for F01 (index_source) |
| `data/02_target/` | Target definitions | Test files only | XML/Excel files containing target field definitions for F02 (index_target) |
| `data/06_template/` | CSV templates | Yes | SAP Migrate Your Data CSV template files |
| `data/07_raw/` | Raw data inputs | Test files only | Raw data files for F04 transformation |

### Output/Report Directories

| Directory | Purpose | Tracked in Git | Description |
|-----------|---------|----------------|-------------|
| `data/03_index_source/` | F01 reports | No (runtime) | HTML/JSON reports from index_source command |
| `data/04_index_target/` | F02 reports | No (runtime) | HTML/JSON reports from index_target command |
| `data/05_map/` | F03 reports | No (runtime) | HTML/JSON reports from map command |
| `data/08_raw_validation/` | Raw validation | No (runtime) | Validation reports before transformation (F04) |
| `data/09_rejected/` | Rejected records | No (runtime) | Records rejected during transformation (F04) |
| `data/10_transformed/` | Final outputs | No (runtime) | Final transformed CSV files for SAP (F04) |
| `data/11_transformed_validation/` | Post-transform validation | No (runtime) | Validation reports after transformation (F04) |

### Logging Directory

| Directory | Purpose | Tracked in Git | Description |
|-----------|---------|----------------|-------------|
| `data/99_logging/` | Log files | No (runtime) | JSONL log files from all pipeline steps |

## Git Tracking Policy

### What is Tracked

1. **Test fixtures**: Files with `test` in the filename (e.g., `test_bnka.xlsx`)
2. **Configuration**: Template files in `data/06_template/`
3. **Directory markers**: `.gitkeep` files to ensure empty directories are tracked
4. **Documentation**: All markdown files in `docs/`

### What is NOT Tracked (Runtime Artifacts)

1. **Reports**: All HTML/JSON/CSV files with timestamps
2. **Logs**: All JSONL files in `data/99_logging/`
3. **Outputs**: All transformed CSV files in `data/10_transformed/`
4. **Validation**: All validation reports in `data/08_raw_validation/` and `data/11_transformed_validation/`
5. **Rejected data**: All files in `data/09_rejected/`
6. **Backup files**: Files matching `*.backup` or `*_backup.*`

## Pipeline Flow

```
F01: index_source
  Input:  data/01_source/{object}_{variant}.xlsx
  Output: migrations/{object}/{variant}/index_source.yaml
  Report: data/03_index_source/index_source_{timestamp}.{html,json}
  Log:    data/99_logging/index_source_{object}_{variant}_{timestamp}.jsonl

F02: index_target
  Input:  data/02_target/{object}_{variant}.xml
  Output: migrations/{object}/{variant}/index_target.yaml
  Report: data/04_index_target/index_target_{timestamp}.{html,json}
  Log:    data/99_logging/index_target_{object}_{variant}_{timestamp}.jsonl

F03: map
  Input:  migrations/{object}/{variant}/index_source.yaml
          migrations/{object}/{variant}/index_target.yaml
  Output: migrations/{object}/{variant}/mapping.yaml
  Report: data/05_map/mapping_{timestamp}.{html,json}
  Log:    data/99_logging/map_{object}_{variant}_{timestamp}.jsonl

F04: transform
  Input:  data/07_raw/{object}_{variant}.xlsx
          data/06_template/S_{VARIANT}#*.csv
          migrations/{object}/{variant}/mapping.yaml
  Output: data/10_transformed/S_{VARIANT}#{object}_Data.csv
  Report: data/08_raw_validation/raw_validation_{object}_{variant}_{timestamp}.{html,json,jsonl}
          data/11_transformed_validation/post_transform_validation_{object}_{variant}_{timestamp}.{html,json,jsonl}
  Log:    data/99_logging/transform_{object}_{variant}_{timestamp}.jsonl
```

## Migrations Directory

```
migrations/
├── object_list.yaml           # Global registry of all objects/variants
└── {object}/                  # Per SAP object (e.g., m140, f100)
    └── {variant}/             # Per table variant (e.g., bnka, cepc)
        ├── index_source.yaml  # F01: Indexed source fields
        ├── index_target.yaml  # F02: Indexed target fields
        ├── mapping.yaml       # F03: Generated field mappings
        ├── validation.yaml    # Validation rules (auto-generated)
        └── transformations.yaml # Value transformation rules
```

## Configuration Directory

```
config/
├── config.yaml                     # Main application configuration
└── central_mapping_memory.yaml     # Reusable mapping rules and overrides
```

## Source Code Structure

```
src/transform_myd_minimal/
├── __init__.py                # Package initialization
├── __main__.py                # Module entry point
├── cli.py                     # CLI command definitions
├── main.py                    # Main orchestration logic
├── config_loader.py           # Configuration loading
├── enhanced_logging.py        # Enhanced logging system
├── reporting.py               # HTML report generation
├── fuzzy.py                   # Fuzzy matching algorithms
├── synonym.py                 # Synonym matching
└── generator.py               # YAML generation logic
```

## Best Practices

### For Development

1. **Never commit runtime outputs**: The `.gitignore` is configured to prevent this
2. **Use test fixtures**: Files with `test` in the name are safe to commit
3. **Check before committing**: Run `git status` to verify no large artifacts are staged
4. **Clean builds**: Use `.gitignore` patterns to exclude build artifacts

### For Operations

1. **Archive logs periodically**: `data/99_logging/` can grow large over time
2. **Clean old reports**: Delete old HTML/JSON reports from `data/0X_*/` directories
3. **Backup test data**: Test fixtures in git are the single source of truth
4. **Document changes**: Update this file when directory structure changes

## Directory Initialization

All data directories include a `.gitkeep` file with a description of the directory's purpose. These files ensure that:

1. Empty directories are tracked in git
2. The directory structure is self-documenting
3. New clones have all required directories

## Troubleshooting

### Directory Not Found Errors

If you encounter "directory not found" errors:

```bash
# Ensure all directories exist
mkdir -p data/{01_source,02_target,03_index_source,04_index_target,05_map,06_template,07_raw,08_raw_validation,09_rejected,10_transformed,11_transformed_validation,99_logging}
```

### Permission Errors

Ensure write permissions for output directories:

```bash
chmod -R u+w data/
```

### Large Repository Size

If the repository becomes large due to accidentally committed artifacts:

1. Check what's tracked: `git ls-files data/`
2. Remove from tracking: `git rm --cached <file>`
3. Update `.gitignore` to prevent recurrence
4. Force push if necessary (coordinate with team)

## See Also

- [USAGE.md](USAGE.md) - Detailed usage examples
- [LOGGING.md](LOGGING.md) - Logging configuration
- [SETUP.md](SETUP.md) - Installation and setup guide
- [README.md](../README.md) - Main project documentation
