# Logging Configuration

Transform MYD Minimal provides rich logging capabilities with different output formats and behaviors for different commands.

## Enhanced Logging for All Commands

All commands (`index_source`, `index_target`, `map`, `transform`) use the enhanced logging system with Rich output, automatic JSONL file logging, and TTY detection.

### Default Behavior

- Logging is **ON by default**
- Automatically writes JSONL events to: `data/99_logging/<step>_<object>_<variant>_<YYYYMMDD_HHmm>.jsonl`
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

**All commands support the same logging options:**

1. **Default operation** (automatic format based on TTY):
   ```bash
   ./transform-myd-minimal index_source --object m140 --variant bnka
   ./transform-myd-minimal index_target --object m140 --variant bnka
   ./transform-myd-minimal map --object m140 --variant bnka
   ./transform-myd-minimal transform --object m140 --variant bnka
   ```

2. **Force JSONL output**:
   ```bash
   ./transform-myd-minimal index_source --object m140 --variant bnka --json
   ```

3. **Quiet mode** (no stdout, but still writes log file):
   ```bash
   ./transform-myd-minimal map --object m140 --variant bnka --quiet
   ```

4. **No log file**:
   ```bash
   ./transform-myd-minimal transform --object m140 --variant bnka --no-log-file
   ```

5. **Custom log file**:
   ```bash
   ./transform-myd-minimal index_target --object m140 --variant bnka --log-file my_custom.jsonl
   ```

6. **Human format without preview table**:
   ```bash
   ./transform-myd-minimal index_source --object m140 --variant bnka --no-preview
   ```

### JSONL Event Format

Events are logged in JSONL format with the following structure:

**index_source**:
```json
{"step":"index_source","object":"m140","variant":"bnka","input_file":"data/01_source/m140_bnka.xlsx","output_file":"migrations/m140/bnka/index_source.yaml","total_columns":4,"duration_ms":420,"warnings":[]}
```

**index_target**:
```json
{"step":"index_target","object":"m140","variant":"bnka","input_file":"data/02_target/m140_bnka.xml","output_file":"migrations/m140/bnka/index_target.yaml","structure":"S_BNKA","total_fields":54,"duration_ms":610,"warnings":[]}
```

### Human Format Output

**index_source** example:
```
✓ index_source  m140/bnka  columns=37
  in:  data/01_source/m140_bnka.xlsx
  out: migrations/m140/bnka/index_source.yaml
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
✓ index_target  m140/bnka  fields=54
  in:  data/02_target/m140_bnka.xml
  out: migrations/m140/bnka/index_target.yaml
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

This provides comprehensive logging and reporting capabilities across all transformation steps.