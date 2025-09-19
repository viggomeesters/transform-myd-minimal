# Transform MYD Minimal - CLI Options Overview

## NEW: Step-by-Step Object+Variant Pipeline (v4.0)

### Available Commands

| Command | Description | Purpose |
|---------|-------------|---------|
| `index_source` | Parse and index source fields from XLSX file | Step 1: Process source headers |
| `index_target` | Parse and index target fields from XML file | Step 2: Process target field definitions |
| `map` | Generate column mapping from indexed files | Step 3: Create source-to-target mappings |

### Command-Specific Options

#### index_source
```bash
./transform-myd-minimal index_source --object OBJECT --variant VARIANT
```
- `--object`: Object name (e.g., m140) **[Required]**
- `--variant`: Variant name (e.g., bnka) **[Required]**

#### index_target  
```bash
./transform-myd-minimal index_target --object OBJECT --variant VARIANT
```
- `--object`: Object name (e.g., m140) **[Required]**
- `--variant`: Variant name (e.g., bnka) **[Required]**

#### map (Updated for v4.0)
```bash
./transform-myd-minimal map --object OBJECT --variant VARIANT [OPTIONS]
```
- `--object`: Object name (e.g., m140) **[Required]**
- `--variant`: Variant name (e.g., bnka) **[Required]**
- `--fuzzy-threshold`: Fuzzy matching threshold (0.0-1.0, default: 0.6)
- `--max-suggestions`: Maximum fuzzy match suggestions (default: 3)
- `--disable-fuzzy`: Disable fuzzy matching completely

### File Path Patterns (v4.0)

#### Input Files
- **Source XLSX**: `data/03_raw/index_source_{object}_{variant}.xlsx`
- **Target XML**: `data/03_raw/index_target_{object}_{variant}.xml`

#### Output Files
- **Object List**: `migrations/object_list.yaml` (global registry)
- **Per Object/Variant**: `migrations/{object}/{variant}/`
  - `index_source.yaml` - Indexed source fields
  - `index_target.yaml` - Indexed target fields
  - `mapping.yaml` - Generated mappings

### Usage Examples (v4.0)

#### Complete Workflow
```bash
# Step 1: Index source fields
./transform-myd-minimal index_source --object m140 --variant bnka

# Step 2: Index target fields  
./transform-myd-minimal index_target --object m140 --variant bnka

# Step 3: Generate mappings
./transform-myd-minimal map --object m140 --variant bnka
```

#### Advanced Mapping Options
```bash
# With custom fuzzy threshold
./transform-myd-minimal map --object m140 --variant bnka --fuzzy-threshold 0.8

# Disable fuzzy matching
./transform-myd-minimal map --object m140 --variant bnka --disable-fuzzy
```

---

## Legacy CLI Options Reference (v3.x)

## Complete CLI Options Reference

| Option | Type | Required | Default | Description | Version Added |
|--------|------|----------|---------|-------------|---------------|
| `-h`, `--help` | flag | No | - | Show help message and exit | v1.0 |
| `--version` | flag | No | - | Show program's version number and exit | v3.0 |
| `map` | subcommand | No* | - | Generate column mapping and YAML files | v3.0 |
| `--object OBJECT` | string | **Yes** | - | Object name (e.g., m140) | v1.0 |
| `--variant VARIANT` | string | **Yes** | - | Variant name (e.g., bnka) | v1.0 |
| `--fuzzy-threshold FUZZY_THRESHOLD` | float | No | 0.6 | Fuzzy matching threshold (0.0-1.0) | v2.0 |
| `--max-suggestions MAX_SUGGESTIONS` | int | No | 3 | Maximum fuzzy match suggestions | v2.0 |
| `--disable-fuzzy` | flag | No | False | Disable fuzzy matching completely | v2.0 |
| `--source-headers-xlsx SOURCE_HEADERS_XLSX` | string | No | config | Path to source headers XLSX file (overrides config) | v3.1 |
| `--source-headers-sheet SOURCE_HEADERS_SHEET` | string | No | config | Sheet name in source XLSX (overrides config) | v3.1 |
| `--source-headers-row SOURCE_HEADERS_ROW` | int | No | config | Header row number in source XLSX (overrides config) | v3.1 |
| `--target-xml TARGET_XML` | string | No | config | Path to target XML file (overrides config) | v3.1 |
| `--target-xml-worksheet TARGET_XML_WORKSHEET` | string | No | config | Worksheet name in target XML (overrides config) | v3.1 |

*The `map` subcommand is optional for backward compatibility. Legacy format without subcommand is supported.

**⚠️ Script Invocation Change:**
With the new src-layout structure, the script is now invoked using the wrapper script `./transform-myd-minimal` instead of directly calling Python files. This provides a cleaner interface without visible `.py` extensions:

- **Old format**: `python3 transform_myd_minimal.py [options]`
- **New format**: `./transform-myd-minimal [options]`

All examples in this document use the new wrapper script format.

## Usage Examples

### Integrated Workflow (Recommended - v3.0+)
```bash
# Generate all YAML files (column_map, fields, value_rules, object_list)
./transform-myd-minimal map --object m140 --variant bnka

# With advanced fuzzy matching options
./transform-myd-minimal map --object m140 --variant bnka --fuzzy-threshold 0.8

# Disable fuzzy matching
./transform-myd-minimal map --object m140 --variant bnka --disable-fuzzy
```

### Legacy Format (Backward Compatible)
```bash
# Legacy format (shows migration message, generates all YAML files)
./transform-myd-minimal -object m140 -variant bnka

# With advanced options
./transform-myd-minimal -object m140 -variant bnka --fuzzy-threshold 0.8
```

### Source-Based Mapping Options (v3.1+)
```bash
# Override source headers file
./transform-myd-minimal map --object m140 --variant bnka --source-headers-xlsx "custom/path/headers.xlsx"

# Override XML target file
./transform-myd-minimal map --object m140 --variant bnka --target-xml "custom/path/targets.xml"

# Override specific worksheet in target XML
./transform-myd-minimal map --object m140 --variant bnka --target-xml-worksheet "Custom Field List"

# Combine multiple source-based overrides
./transform-myd-minimal map --object m140 --variant bnka \
  --source-headers-xlsx "data/custom_headers.xlsx" \
  --source-headers-sheet "Sheet2" \
  --target-xml "data/custom_targets.xml"
```

### Advanced Fuzzy Matching Options
```bash
# High precision fuzzy matching (stricter threshold)
./transform-myd-minimal map --object m140 --variant bnka --fuzzy-threshold 0.8

# More fuzzy suggestions
./transform-myd-minimal map --object m140 --variant bnka --max-suggestions 5

# Combined advanced options
./transform-myd-minimal map --object m140 --variant bnka --fuzzy-threshold 0.7 --max-suggestions 2
```

### Getting Help
```bash
# Show all available commands
./transform-myd-minimal --help

# Show map command options
./transform-myd-minimal map --help

# Show version information
./transform-myd-minimal --version
```

## Parameter Details

### Required Parameters

#### `--object`
- **Purpose**: Specifies the object name for the transformation
- **Format**: String, typically alphanumeric (e.g., "m140", "p100")
- **Usage**: Determines the input Excel file path: `data/02_fields/fields_{object}_{variant}.xlsx`
- **Example**: `--object m140`

#### `--variant` 
- **Purpose**: Specifies the variant name for the transformation
- **Format**: String, typically alphanumeric (e.g., "bnka", "test")
- **Usage**: Determines both input file and output directory paths
- **Example**: `--variant bnka`

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

### Source-Based Mapping Parameters (v3.1+)

#### `--source-headers-xlsx`
- **Purpose**: Overrides the source headers XLSX file path from config
- **Format**: File path string (relative or absolute)
- **Default**: Uses `mapping.source_headers.path` from config.yaml
- **Example**: `--source-headers-xlsx "data/custom_headers.xlsx"`

#### `--source-headers-sheet`
- **Purpose**: Overrides the sheet name in the source headers XLSX
- **Format**: String (sheet name)
- **Default**: Uses `mapping.source_headers.sheet` from config.yaml
- **Example**: `--source-headers-sheet "Sheet2"`

#### `--source-headers-row`
- **Purpose**: Overrides the header row number in the source XLSX
- **Format**: Integer (1-based row number)
- **Default**: Uses `mapping.source_headers.header_row` from config.yaml
- **Example**: `--source-headers-row 2`

#### `--target-xml`
- **Purpose**: Overrides the target XML file path from config
- **Format**: File path string (relative or absolute)
- **Default**: Uses `mapping.target_xml.path` from config.yaml
- **Example**: `--target-xml "data/custom_targets.xml"`

#### `--target-xml-worksheet`
- **Purpose**: Overrides the worksheet name in the target XML
- **Format**: String (worksheet name)
- **Default**: Uses `mapping.target_xml.worksheet_name` from config.yaml
- **Example**: `--target-xml-worksheet "Custom Field List"`

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
- **Global Config Files**: `output/object_list.yaml`, `output/mapping.yaml`, `output/targets.yaml`
- **Migration Structure**: `migrations/{OBJECT}/{table}/fields.yaml`, `migrations/{OBJECT}/{table}/mappings.yaml`, etc.
- **Example**: `migrations/M140/bnka/`

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
./transform-myd-minimal -object m140 -variant bnka

# v3.0 integrated workflow (recommended)
./transform-myd-minimal map --object m140 --variant bnka
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
./transform-myd-minimal -object m140 -variant bnka

# v2.0 with advanced features
./transform-myd-minimal map --object m140 --variant bnka --fuzzy-threshold 0.7
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