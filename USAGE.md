# Usage Guide - Transform MYD Minimal

This guide provides end-to-end examples for using Transform MYD Minimal with expected file locations and outputs.

## Overview

Transform MYD Minimal processes SAP migration data through a 4-step pipeline:

1. **F01 - index_source**: Parse source Excel headers → `migrations/<object>/<variant>/index_source.yaml`
2. **F02 - index_target**: Parse target XML fields → `migrations/<object>/<variant>/index_target.yaml`  
3. **F03 - map**: Generate field mappings → `migrations/<object>/<variant>/mapping.yaml`
4. **F04 - transform**: Transform raw data → CSV files in `data/07_transformed/`

## Directory Structure

```
project/
├── data/
│   ├── 01_source/               # F01 inputs
│   │   └── m140_bnka.xlsx      # Source headers
│   ├── 02_target/               # F02 inputs  
│   │   └── m140_bnka.xml
│   ├── 03_templates/            # F04 templates
│   │   └── S_BNKA#template.csv 
│   ├── 03_raw/                  # F04 inputs
│   │   └── m140_bnka.xlsx       # Raw data
│   ├── 05_raw_validation/       # F04 validation outputs
│   ├── 06_rejected/             # F04 rejected records
│   ├── 07_transformed/          # F04 final outputs
│   ├── 08_transformed_validation/ # F04 post-transform validation
│   └── 09_logging/              # All log files
└── migrations/
    └── m140/
        └── bnka/
            ├── index_source.yaml    # F01 output
            ├── index_target.yaml    # F02 output
            └── mapping.yaml         # F03 output
```

## Complete Example Workflow

### Example: Object `m140`, Variant `bnka`

#### Step 1: F01 - Index Source Fields

**Input Required:**
- `data/01_source/m140_bnka.xlsx` - Excel file with source system headers

**Commands:**
```bash
# Linux/macOS
./transform-myd-minimal index_source --object m140 --variant bnka

# Windows PowerShell
python -m transform_myd_minimal index_source --object m140 --variant bnka
```

**Outputs:**
- `migrations/m140/bnka/index_source.yaml` - Parsed source fields
- `data/09_logging/index_source_m140_bnka_20240922_1430.jsonl` - Operation log

**Example Output Structure:**
```yaml
metadata:
  object: m140
  variant: bnka
  input_file: data/01_source/m140_bnka.xlsx
  generated_at: '2024-09-22T14:30:15'
  structure: S_BNKA
  source_fields_count: 25

source_fields:
  - field_name: BUKRS
    dtype: string
    nullable: true
    example: null
  - field_name: HKONT
    dtype: string 
    nullable: true
    example: null
```

#### Step 2: F02 - Index Target Fields

**Input Required:**
- `data/02_target/m140_bnka.xml` - SpreadsheetML with target definitions

**Commands:**
```bash
# Linux/macOS
./transform-myd-minimal index_target --object m140 --variant bnka

# Windows PowerShell  
python -m transform_myd_minimal index_target --object m140 --variant bnka
```

**Outputs:**
- `migrations/m140/bnka/index_target.yaml` - Parsed target fields
- `migrations/m140/bnka/validation.yaml` - Generated validation rules (if not exists)
- `data/09_logging/index_target_m140_bnka_20240922_1431.jsonl` - Operation log

**Example Output Structure:**
```yaml
metadata:
  object: m140
  variant: bnka
  target_file: data/02_target/m140_bnka.xml
  generated_at: '2024-09-22T14:31:20'
  structure: S_BNKA
  target_fields_count: 30

target_fields:
  - field_name: S_BNKA.BUKRS
    field_description: Company Code
    data_type: Text
    length: 4
    key_field: true
    mandatory: true
```

#### Step 3: F03 - Generate Mapping

**Inputs Required:**
- `migrations/m140/bnka/index_source.yaml` (from Step 1)
- `migrations/m140/bnka/index_target.yaml` (from Step 2)

**Commands:**
```bash
# Linux/macOS
./transform-myd-minimal map --object m140 --variant bnka

# Windows PowerShell
python -m transform_myd_minimal map --object m140 --variant bnka
```

**Outputs:**
- `migrations/m140/bnka/mapping.yaml` - Field mappings with confidence scores
- `data/09_logging/map_m140_bnka_20240922_1432.jsonl` - Operation log

**Example Output Structure:**
```yaml
metadata:
  object: m140
  variant: bnka
  generated_at: '2024-09-22T14:32:10'
  source_index: migrations/m140/bnka/index_source.yaml
  target_index: migrations/m140/bnka/index_target.yaml


mappings:
- target_table: S_BNKA
  target_field: BUKRS
  source_header: BUKRS
  required: true
  transforms: []
  confidence: 1.0
  status: mapped
  rationale: Exact match


to_audit:
- target_field: S_BNKA.SPECIAL_FIELD
  reason: Low confidence mapping
  confidence: 0.3


unmapped_source_fields:
- LEGACY_FIELD_1
- OBSOLETE_CODE


unmapped_target_fields:
- S_BNKA.NEW_FIELD
- S_BNKA.OPTIONAL_FIELD
```

#### Step 4: F04 - Transform Data

**Inputs Required:**
- `data/03_raw/m140_bnka.xlsx` - Raw data to transform
- `migrations/m140/bnka/mapping.yaml` (from Step 3)
- `migrations/m140/bnka/index_target.yaml` (from Step 2)
- `data/03_templates/S_BNKA#*.csv` - CSV template files

**Commands:**
```bash
# Linux/macOS
./transform-myd-minimal transform --object m140 --variant bnka

# Windows PowerShell
python -m transform_myd_minimal transform --object m140 --variant bnka
```

**Outputs:**
- `data/07_transformed/S_BNKA#m140_Data.csv` - Primary SAP upload file
- `data/07_transformed/S_BNKA#m140_20240922_1433_output.csv` - Timestamped snapshot
- `data/06_rejected/rejected_m140_bnka_20240922_1433.csv` - Rejected records
- `data/05_raw_validation/raw_validation_m140_bnka_20240922_1433.csv` - Pre-transform validation
- `data/08_transformed_validation/post_transform_validation_m140_bnka_20240922_1433.csv` - Post-transform validation
- `data/09_logging/transform_m140_bnka_20240922_1433.jsonl` - Operation log

## CLI Options

### Global Options (All Commands)
- `--help` - Show command help
- `--json` - Force JSONL output to stdout
- `--quiet` - No stdout output; still writes log file unless --no-log-file
- `--no-log-file` - Disable automatic log file writing
- `--log-file PATH` - Override default log file path
- `--root PATH` - Override root directory (default: .)

### F01/F02 Specific Options  
- `--format {human,jsonl}` - Override TTY detection for output format
- `--no-preview` - Suppress preview table in human mode
- `--force` - Overwrite existing output files

### F03 Specific Options
- `--fuzzy-threshold FLOAT` - Fuzzy matching threshold (0.0-1.0, default: 0.6)
- `--max-suggestions INT` - Maximum fuzzy match suggestions (default: 3)
- `--disable-fuzzy` - Disable fuzzy matching completely

## Logging Behavior

### Default Behavior
- **TTY Detection**: Human-readable output in terminal, JSONL when piped
- **Log Files**: Always written to `data/09_logging/` unless `--no-log-file`
- **Path Format**: Forward slashes in all printed paths (Windows compatible)

### Examples
```bash
# Default: Human output + log file
python -m transform_myd_minimal index_source --object m140 --variant bnka

# Force JSON output + log file
python -m transform_myd_minimal index_source --object m140 --variant bnka --json

# Quiet mode: Only log file, no stdout
python -m transform_myd_minimal index_source --object m140 --variant bnka --quiet

# No log file, human output only
python -m transform_myd_minimal index_source --object m140 --variant bnka --no-log-file

# Custom log file location
python -m transform_myd_minimal index_source --object m140 --variant bnka --log-file /custom/path/my_log.jsonl
```

## Error Handling

### Exit Codes
- **0**: Success
- **1**: General exception
- **2**: Missing input file
- **3**: Missing index/headers
- **4**: No fields/targets found
- **5**: Would overwrite (use --force)
- **6**: Invalid validation configuration

### Common Issues

#### Missing Input Files
```bash
# Error: data/01_source/m140_bnka.xlsx not found
$ python -m transform_myd_minimal index_source --object m140 --variant bnka
Error: Input file not found: data/01_source/m140_bnka.xlsx
# Exit code: 2
```

#### Overwrite Protection
```bash
# Error: Output exists and --force not specified
$ python -m transform_myd_minimal index_source --object m140 --variant bnka
Error: Output file exists: migrations/m140/bnka/index_source.yaml. Use --force to overwrite.
# Exit code: 5

# Solution: Use --force flag
$ python -m transform_myd_minimal index_source --object m140 --variant bnka --force
```

## Troubleshooting

### Windows PowerShell Issues
Always use `python -m transform_myd_minimal` instead of the console script if you encounter module loading issues.

### File Path Issues
- Use forward slashes in configuration files even on Windows
- Check that input files exist with exact case-sensitive names
- Verify directory permissions for output locations

### Memory Issues with Large Files
- Process files in smaller batches if possible
- Monitor memory usage during transformation
- Consider increasing available memory for Python process