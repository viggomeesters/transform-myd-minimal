# Logging Configuration

Transform MYD Minimal provides rich logging capabilities with different output formats and behaviors for different commands.

## Enhanced Logging for F01/F02 Commands

The `index_source` and `index_target` commands use an enhanced logging system with Rich output, automatic JSONL file logging, and TTY detection.

### Default Behavior

- Logging is **ON by default**
- Automatically writes JSONL events to: `data/09_logging/<step>_<object>_<variant>_<YYYYMMDD_HHmm>.jsonl`
- **TTY detection**: 
  - Terminal (interactive) → Human-readable summary with Rich formatting and preview tables
  - Non-TTY (piped/redirected) → JSONL lines
- Uses forward slashes in all printed paths
- Measures and emits `duration_ms` for all operations

### CLI Flags

Use these flags to control logging behavior:

- `--json`: Force JSONL output to stdout (shorthand for `--format jsonl`)
- `--format [human|jsonl]`: Override TTY detection for output format
- `--log-file PATH`: Override the default log file path
- `--no-log-file`: Disable writing to log file
- `--no-preview`: Suppress preview table in human mode
- `--quiet`: No stdout output; still writes file unless `--no-log-file`

**Precedence for stdout format**: `quiet` > `json` > `format` > TTY detection

### Examples

1. **Default operation** (automatic format based on TTY):
   ```bash
   python -m transform_myd_minimal index_source --object m143 --variant bnka
   ```

2. **Force JSONL output**:
   ```bash
   python -m transform_myd_minimal index_source --object m143 --variant bnka --json
   ```

3. **Quiet mode** (no stdout, but still writes log file):
   ```bash
   python -m transform_myd_minimal index_source --object m143 --variant bnka --quiet
   ```

4. **No log file**:
   ```bash
   python -m transform_myd_minimal index_source --object m143 --variant bnka --no-log-file
   ```

5. **Custom log file**:
   ```bash
   python -m transform_myd_minimal index_source --object m143 --variant bnka --log-file my_custom.jsonl
   ```

6. **Human format without preview table**:
   ```bash
   python -m transform_myd_minimal index_source --object m143 --variant bnka --no-preview
   ```

### JSONL Event Format

Events are logged in JSONL format with the following structure:

**index_source**:
```json
{"step":"index_source","object":"m143","variant":"bnka","input_file":"data/01_source/index_source_m143_bnka.xlsx","output_file":"migrations/m143/bnka/index_source.yaml","total_columns":4,"duration_ms":420,"warnings":[]}
```

**index_target**:
```json
{"step":"index_target","object":"m143","variant":"bnka","input_file":"data/02_target/index_target_m143_bnka.xml","output_file":"migrations/m143/bnka/index_target.yaml","structure":"S_BNKA","total_fields":54,"duration_ms":610,"warnings":[]}
```

### Human Format Output

**index_source** example:
```
✓ index_source  m143/bnka  columns=37
  in:  data/01_source/m143_bnka.xlsx
  out: migrations/m143/bnka/index_source.yaml
  time: 420ms
  warnings: 0

Headers (sample):
┏━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━┓
┃ # ┃ field_name               ┃ dtype  ┃ nullable ┃ example ┃
┡━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━┩
│ 1 │ Bank Country/Region Key  │ string │ false    │ NL      │
│ 2 │ Bank Key                 │ string │ true     │ 123456  │
└───┴──────────────────────────┴────────┴──────────┴─────────┘
```

**index_target** example:
```
✓ index_target  m143/bnka  fields=54
  in:  data/02_target/index_target_m143_bnka.xml
  out: migrations/m143/bnka/index_target.yaml
  structure: S_BNKA
  time: 610ms
  warnings: 0

Fields (sample):
┏━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━┓
┃ sap_field ┃ field_description ┃ mandatory ┃ data_type ┃ length ┃ decimal ┃ field_group ┃ key   ┃
┡━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━┩
│ banks     │ Bank Country Key  │ True      │ CHAR      │ 3      │ 0       │ key         │ True  │
│ bankl     │ Bank Number       │ True      │ CHAR      │ 15     │ 0       │ key         │ True  │
└───────────┴───────────────────┴───────────┴───────────┴────────┴─────────┴─────────────┴───────┘
```

## Legacy Logging for Map Command

The `map` command continues to use the standard Python logging system:

- **INFO**: Progress updates, statistics, successful operations
- **WARNING**: Non-fatal issues (e.g., missing config files, failed optional operations)  
- **ERROR**: Fatal errors that prevent operation completion

This provides control over what information is displayed based on importance.