# Copilot Agent Quick Start Example

This file provides a simple example for Copilot agents to understand how to work with the Transform MYD Minimal tool.

## Quick Test Commands

```bash
# 1. Verify installation and dependencies
pip install -r requirements.txt

# 2. Test basic CLI functionality
./transform-myd-minimal --help
./transform-myd-minimal map --help

# 3. Check version information
./transform-myd-minimal --version

# 4. Test package installation
pip install -e .
transform-myd-minimal --version
```

## Understanding the Tool Output

When you run a mapping command like:
```bash
./transform-myd-minimal map -object m140 -variant bnka
```

The tool will:
1. Look for input file: `data/02_fields/fields_m140_bnka.xlsx`
2. Generate outputs in two locations:
   - Legacy: `config/m140/bnka/` (column_map.yaml, fields.yaml, value_rules.yaml)
   - New: `migrations/M140/bnka/` (fields.yaml, mappings.yaml, validation.yaml, transformations.yaml)
3. Show matching statistics in console output

## Example Console Output

```
=== Advanced Matching Results ===
Exact matches: 11
Fuzzy/Synonym matches: 2
Unmapped sources: 26
Audit matches (fuzzy to exact-mapped targets): 1
Mapping coverage: 33.3%

Central memory skip rules applied: 2
Central memory manual mappings applied: 1

Fuzzy matches found:
  BANK_NAME → BANKL (fuzzy, confidence: 0.75, algorithm: levenshtein)
  ACCOUNT_TYPE → KONTY (fuzzy, confidence: 0.68, algorithm: jaro_winkler)
```

## Key Files to Understand

- **CLI Entry Point**: `src/transform_myd_minimal/cli.py` - Command parsing
- **Core Logic**: `src/transform_myd_minimal/main.py` - Matching algorithms
- **YAML Generation**: `src/transform_myd_minimal/generator.py` - File output
- **Configuration**: `src/transform_myd_minimal/config_loader.py` - Settings management

## Common Agent Tasks

### 1. Debugging a Matching Issue
```bash
# Run with more verbose output
./transform-myd-minimal map -object m140 -variant bnka --max-suggestions 10 --fuzzy-threshold 0.4
```

### 2. Adding a New Synonym
Edit `src/transform_myd_minimal/synonym.py`:
```python
def get_synonyms(self) -> Dict[str, List[str]]:
    return {
        # Add new synonym mapping
        "customer": ["klant", "client", "kunde"],
        # ... existing mappings
    }
```

### 3. Adjusting Fuzzy Matching
Edit configuration in `configs/config.yaml`:
```yaml
fuzzy_threshold: 0.7  # Increase for stricter matching
max_suggestions: 5    # Show more potential matches
disable_fuzzy: false  # Set to true to disable fuzzy matching
```

## Testing Your Changes

After making modifications:

1. **Test CLI still works**:
   ```bash
   ./transform-myd-minimal --help
   ```

2. **Verify package installation**:
   ```bash
   pip install -e .
   transform-myd-minimal --version
   ```

3. **Run with sample data** (if available):
   ```bash
   ./transform-myd-minimal map -object m140 -variant bnka
   ```

4. **Check output structure**:
   ```bash
   # Verify files are generated
   ls -la config/m140/bnka/
   ls -la migrations/M140/bnka/
   ```

## Error Troubleshooting

Common errors and solutions:

- **ModuleNotFoundError**: Install dependencies with `pip install -r requirements.txt`
- **FileNotFoundError**: Ensure Excel file exists at expected path `data/02_fields/fields_{object}_{variant}.xlsx`
- **Permission errors**: Check write permissions for output directories
- **YAML syntax errors**: Validate generated YAML files with `python -c "import yaml; yaml.safe_load(open('file.yaml'))"`