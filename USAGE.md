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
│   ├── 03_index_source/         # F01 HTML/JSON reports
│   ├── 04_index_target/         # F02 HTML/JSON reports
│   ├── 05_map/                  # F03 HTML/JSON reports
│   ├── 06_template/             # F04 templates
│   │   └── S_BNKA#template.csv 
│   ├── 07_raw/                  # F04 inputs
│   │   └── m140_bnka.xlsx       # Raw data
│   ├── 08_raw_validation/       # F04 validation outputs
│   ├── 09_rejected/             # F04 rejected records
│   ├── 10_transformed/          # F04 final outputs
│   ├── 11_transformed_validation/ # F04 post-transform validation
│   └── 99_logging/              # All log files
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
- `data/99_logging/index_source_m140_bnka_20240922_1430.jsonl` - Operation log

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
- `data/99_logging/index_target_m140_bnka_20240922_1431.jsonl` - Operation log

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
- `data/99_logging/map_m140_bnka_20240922_1432.jsonl` - Operation log

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
- `data/11_transformed_validation/post_transform_validation_m140_bnka_20240922_1433.csv` - Post-transform validation
- `data/99_logging/transform_m140_bnka_20240922_1433.jsonl` - Operation log

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
- **Log Files**: Always written to `data/99_logging/` unless `--no-log-file`
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

## HTML Reporting

Transform MYD Minimal automatically generates interactive HTML reports for all F01–F04 steps alongside JSON summaries.

### HTML Report Features

- **Self-contained**: No external dependencies, all CSS/JS embedded inline
- **Interactive**: Client-side table sorting, filtering, and search
- **Visual**: KPI cards, bar charts using inline SVG
- **Export**: CSV download buttons for all data tables
- **Mobile-friendly**: Responsive design that works on all devices

### Report Locations

**F01-F03 Reports**:
```
data/03_index_source/
├── index_source_20240922_1432.html     # F01: Source headers analysis
└── index_source_20240922_1432.json

data/04_index_target/
├── index_target_20240922_1433.html     # F02: Target fields analysis  
└── index_target_20240922_1433.json

data/05_map/
├── mapping_20240922_1434.html          # F03: Mapping results
└── mapping_20240922_1434.json
```

**F04 Reports** (validation):
```
data/08_raw_validation/
├── raw_validation_m140_bnka_20240922_1435.html     # Raw data validation
├── raw_validation_m140_bnka_20240922_1435.json
└── raw_validation_m140_bnka_20240922_1435.jsonl

data/11_transformed_validation/  
├── post_transform_validation_m140_bnka_20240922_1435.html  # Post-transform validation
├── post_transform_validation_m140_bnka_20240922_1435.json
└── post_transform_validation_m140_bnka_20240922_1435.jsonl
```

### Example Usage

```bash
# Default: Generate HTML + JSON reports
python -m transform_myd_minimal index_source --object m140 --variant bnka
# Output: report: migrations/m140/bnka/reports/index_source_20240922_1432.html

# Skip HTML generation (JSON only)
python -m transform_myd_minimal map --object m140 --variant bnka --no-html

# Custom report directory
python -m transform_myd_minimal transform --object m140 --variant bnka --html-dir /custom/reports
```

### Report Content by Step

**F01 (index_source)** - Source Headers Analysis:
- **KPIs**: Total columns, duplicates count, empty headers
- **Chart**: N/A (header analysis)
- **Tables**: Headers (field name, dtype, nullable, example)
- **Lists**: Duplicate headers, warnings
- **Downloads**: headers.csv

**F02 (index_target)** - Target Fields Analysis:
- **KPIs**: Total fields, mandatory fields, key fields  
- **Chart**: Field groups distribution (key vs control data)
- **Tables**: Target fields (SAP field, table, mandatory, key, data type, length)
- **Lists**: Anomalies, validation scaffold status
- **Downloads**: target_fields.csv

**F03 (map)** - Mapping Results:
- **KPIs**: Mapped, unmapped, to-audit, unused sources
- **Chart**: N/A (mapping analysis)
- **Tables**: Mappings (target field, source header, confidence, status, rationale), To-audit items
- **Lists**: Unmapped source fields, unmapped target fields
- **Downloads**: mappings.csv, to_audit.csv, unmapped_sources.csv, unmapped_targets.csv

**F04 (transform)** - Validation Reports:

*RAW Validation (Step 2):*
- **KPIs**: Rows in, missing sources count
- **Chart**: Top null rates by source column  
- **Tables**: Null rates by source (column, percentage)
- **Lists**: Missing source columns
- **Downloads**: null_rates.csv, missing_sources.csv

*POST Validation (Step 8):*
- **KPIs**: Rows in/out/rejected, mapped coverage percentage
- **Chart**: Top errors by validation rule
- **Tables**: Errors by rule, errors by field, sample rejected rows
- **Lists**: Ignored target fields
- **Downloads**: errors_by_rule.csv, errors_by_field.csv, sample_rows.csv
- **Footer**: CSV export requirements (UTF-8, CRLF, etc.)

### Accessing Reports

HTML reports are self-contained and can be:
- Opened directly in any web browser
- Shared via email or file transfer
- Hosted on web servers for team access
- Archived for audit purposes

The embedded JSON data in each HTML report (in `<script id="data">` tag) can be extracted for further analysis or integration with other tools.

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