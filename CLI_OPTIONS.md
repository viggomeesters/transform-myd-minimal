# Transform MYD Minimal - CLI Options Overview

## Complete CLI Options Reference

| Option | Type | Required | Default | Description | Version Added |
|--------|------|----------|---------|-------------|---------------|
| `-h`, `--help` | flag | No | - | Show help message and exit | v1.0 |
| `--version` | flag | No | - | Show version information and exit | v3.0 |
| `map` | subcommand | No* | - | Generate column mapping and YAML files | v3.0 |
| `-object OBJECT`, `--object OBJECT` | string | **Yes** | - | Object name (e.g., m140) | v1.0 |
| `-variant VARIANT`, `--variant VARIANT` | string | **Yes** | - | Variant name (e.g., bnka) | v1.0 |
| `--fuzzy-threshold FUZZY_THRESHOLD` | float | No | 0.6 | Fuzzy matching threshold (0.0-1.0) | v2.0 |
| `--max-suggestions MAX_SUGGESTIONS` | int | No | 3 | Maximum fuzzy match suggestions | v2.0 |
| `--disable-fuzzy` | flag | No | False | Disable fuzzy matching completely | v2.0 |

*The `map` subcommand is optional for backward compatibility. Legacy format without subcommand is supported.

## Usage Examples

### Integrated Workflow (Recommended - v3.0+)
```bash
# Generate all YAML files (column_map, fields, value_rules, object_list)
python3 transform_myd_minimal.py map -object m140 -variant bnka

# With advanced fuzzy matching options
python3 transform_myd_minimal.py map -object m140 -variant bnka --fuzzy-threshold 0.8

# Disable fuzzy matching
python3 transform_myd_minimal.py map -object m140 -variant bnka --disable-fuzzy
```

### Legacy Format (Backward Compatible)
```bash
# Legacy format (shows migration message, generates all YAML files)
python3 transform_myd_minimal.py -object m140 -variant bnka

# With advanced options
python3 transform_myd_minimal.py -object m140 -variant bnka --fuzzy-threshold 0.8
```

### Advanced Fuzzy Matching Options
```bash
# High precision fuzzy matching (stricter threshold)
python3 transform_myd_minimal.py map -object m140 -variant bnka --fuzzy-threshold 0.8

# More fuzzy suggestions
python3 transform_myd_minimal.py map -object m140 -variant bnka --max-suggestions 5

# Combined advanced options
python3 transform_myd_minimal.py map -object m140 -variant bnka --fuzzy-threshold 0.7 --max-suggestions 2
```

### Getting Help
```bash
# Show all available commands
python3 transform_myd_minimal.py --help

# Show map command options
python3 transform_myd_minimal.py map --help

# Show version information
python3 transform_myd_minimal.py --version
```

## Parameter Details

### Required Parameters

#### `-object` / `--object`
- **Purpose**: Specifies the object name for the transformation
- **Format**: String, typically alphanumeric (e.g., "m140", "p100")
- **Usage**: Determines the input Excel file path: `data/02_fields/fields_{object}_{variant}.xlsx`
- **Example**: `-object m140`

#### `-variant` / `--variant` 
- **Purpose**: Specifies the variant name for the transformation
- **Format**: String, typically alphanumeric (e.g., "bnka", "test")
- **Usage**: Determines both input file and output directory paths
- **Example**: `-variant bnka`

### Advanced Matching Parameters (v2.0+)

#### `--fuzzy-threshold`
- **Purpose**: Controls the minimum similarity score required for fuzzy matches
- **Range**: 0.0 to 1.0 (decimal values)
- **Default**: 0.6 (60% similarity)
- **Impact**: 
  - Higher values (0.8-1.0): Fewer but more accurate matches
  - Lower values (0.4-0.6): More matches but potentially less accurate
- **Examples**:
  - `--fuzzy-threshold 0.8` (strict matching)
  - `--fuzzy-threshold 0.4` (loose matching)

#### `--max-suggestions`
- **Purpose**: Limits the number of fuzzy match suggestions returned
- **Range**: Positive integers (1-10 recommended)
- **Default**: 3
- **Impact**: Controls console output verbosity and processing time
- **Examples**:
  - `--max-suggestions 1` (only best match)
  - `--max-suggestions 5` (up to 5 suggestions)

#### `--disable-fuzzy`
- **Purpose**: Completely disables fuzzy matching algorithms
- **Type**: Boolean flag (no value required)
- **Default**: False (fuzzy matching enabled)
- **Impact**: Falls back to exact and synonym matching only
- **Use cases**: 
  - Performance optimization for large datasets
  - When only high-confidence matches are desired
  - Debugging exact matching behavior

## Exit Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 0 | Success | Transformation completed successfully |
| 1 | Error | General error (file not found, invalid parameters, etc.) |

## File Path Patterns

### Input Files
- **Excel Input**: `data/02_fields/fields_{object}_{variant}.xlsx`
- **Example**: `data/02_fields/fields_m140_bnka.xlsx`

### Output Files  
- **Column Mapping**: `config/{object}/{variant}/column_map.yaml`
- **Field Definitions**: `config/{object}/{variant}/fields.yaml`  
- **Value Rules**: `config/{object}/{variant}/value_rules.yaml`
- **Object Overview**: `config/object_list.yaml`
- **Example**: `config/m140/bnka/`

## Changelog

### Version 3.0 (Integrated Workflow) - Current
**Added:**
- `map` subcommand for integrated YAML generation workflow
- Automatic generation of `fields.yaml` per table with comprehensive field information
- Automatic generation of `value_rules.yaml` per table with intelligent rule detection
- Automatic generation/update of `object_list.yaml` master overview
- Integrated workflow that generates all YAML files in a single command
- Backward compatibility with legacy command format
- Migration messages for legacy usage

**Changed:**
- Command structure now supports subcommands (map)
- All YAML files generated automatically in single workflow
- Enhanced output includes 4 different YAML file types
- Improved user experience with integrated approach

### Version 2.0 (Advanced Matching) - Legacy
**Added:**
- `--fuzzy-threshold`: Configurable fuzzy matching threshold
- `--max-suggestions`: Configurable maximum suggestions limit  
- `--disable-fuzzy`: Option to disable fuzzy matching
- Advanced field matching system with Levenshtein and Jaro-Winkler algorithms
- Synonym matching with NL/EN dictionary
- Enhanced console output with matching statistics
- YAML version 2 format with algorithm metadata

**Changed:**
- Description updated to "Advanced Version"
- Enhanced help text with parameter descriptions
- Output format includes matching statistics and confidence scores

### Version 1.0 (Basic Matching) - Legacy
**Initial Features:**
- `-object`: Basic object name parameter
- `-variant`: Basic variant name parameter  
- `-h`/`--help`: Standard help functionality
- Simple exact matching algorithm
- Basic YAML output format
- Smart transformation logic for derived targets

## Migration Guide

### From v2.0 to v3.0 (Recommended)
Upgrade to the integrated workflow for automatic YAML generation:

```bash
# v2.0 command (still works, shows migration message)
python3 transform_myd_minimal.py -object m140 -variant bnka

# v3.0 integrated workflow (recommended)
python3 transform_myd_minimal.py map -object m140 -variant bnka
```

**Benefits of v3.0:**
- Single command generates all required YAML files
- Automatic field definitions and value rules
- Updated object overview list
- Streamlined workflow

### From v1.0 to v2.0
All existing commands continue to work without changes. New features are opt-in:

```bash
# v1.0 command (still works)
python3 transform_myd_minimal.py -object m140 -variant bnka

# v2.0 with advanced features
python3 transform_myd_minimal.py map -object m140 -variant bnka --fuzzy-threshold 0.7
```

## Tips and Best Practices

### Performance Optimization
- Use `--disable-fuzzy` for large datasets where speed is critical
- Increase `--fuzzy-threshold` to reduce processing time
- Reduce `--max-suggestions` to minimize console output

### Accuracy Tuning
- Start with default settings (`--fuzzy-threshold 0.6`)
- Increase threshold for stricter matching: `--fuzzy-threshold 0.8`
- Decrease threshold for more suggestions: `--fuzzy-threshold 0.4`
- Review console output to assess match quality

### Debugging
- Use `--disable-fuzzy` to isolate exact matching issues
- Increase `--max-suggestions` to see more potential matches
- Lower `--fuzzy-threshold` to understand why matches might be missed

---

*This document is automatically updated as new CLI options are added.*