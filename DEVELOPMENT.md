# Development Setup Guide

## Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

## Quick Setup

### 1. Clone the Repository
```bash
git clone https://github.com/viggomeesters/transform-myd-minimal.git
cd transform-myd-minimal
```

### 2. Install Dependencies
```bash
# Install required dependencies
pip install -r requirements.txt

# Or install using pyproject.toml
pip install -e .

# Optional: Install development dependencies
pip install -e ".[dev]"
```

### 3. Verify Installation
```bash
# Test CLI functionality
./transform-myd-minimal --help
./transform-myd-minimal map --help

# Or run via Python module
python -m src.transform_myd_minimal --help
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
│       ├── fuzzy.py                    # Fuzzy matching algorithms
│       ├── generator.py                # YAML generation logic
│       └── synonym.py                  # Synonym matching logic
├── transform-myd-minimal               # Wrapper script for easy execution
├── configs/                            # Configuration directory
│   ├── config.yaml                     # Application settings (if exists)
│   └── central_mapping_memory.yaml     # Central mapping rules (if exists)
├── config/                             # Generated output (legacy structure)
├── data/                               # Input Excel files
│   └── 02_fields/                      # Expected input directory
├── migrations/                         # Generated output (new structure)
├── requirements.txt                    # Python dependencies
├── pyproject.toml                      # Modern Python project configuration
└── README.md                          # Main project documentation
```

## Running the Tool

### Basic Usage
```bash
# Generate mapping files for an object/variant combination
./transform-myd-minimal map -object m140 -variant bnka

# View available options
./transform-myd-minimal map --help
```

### Advanced Options
```bash
# Adjust fuzzy matching threshold
./transform-myd-minimal map -object m140 -variant bnka --fuzzy-threshold 0.8

# Disable fuzzy matching for faster processing
./transform-myd-minimal map -object m140 -variant bnka --disable-fuzzy

# Increase number of suggestions shown
./transform-myd-minimal map -object m140 -variant bnka --max-suggestions 10
```

### Input Requirements
The tool expects Excel files in the format:
- Path: `data/02_fields/fields_{object}_{variant}.xlsx`
- Content: Must contain `field`, `field_name`, and `field_description` columns
- Structure: Rows marked as 'Source' and 'Target' in the `field` column

## Configuration

### Application Settings (`configs/config.yaml`)
```yaml
# Fuzzy matching configuration
fuzzy_threshold: 0.6        # Matching threshold (0.0-1.0)
max_suggestions: 3          # Maximum suggestions to show
disable_fuzzy: false        # Whether to disable fuzzy matching

# Directory configuration  
input_dir: "data/02_fields" # Input directory for Excel files
output_dir: "config"        # Output directory for generated files
```

### Central Mapping Memory (`configs/central_mapping_memory.yaml`)
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
   ./transform-myd-minimal map -object m140 -variant bnka
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