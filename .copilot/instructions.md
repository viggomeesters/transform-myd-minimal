# Copilot Agent Instructions for Transform MYD Minimal

## Working with This Codebase

### Code Organization
- **Primary package**: `src/transform_myd_minimal/` - all core functionality
- **Entry point**: Can be run via `./transform-myd-minimal` wrapper or `python -m transform_myd_minimal`
- **Module structure**: Each module has a specific responsibility (CLI, matching, generation, etc.)

### Dependencies Management
- Install with: `pip install pandas openpyxl pyyaml`
- No requirements.txt currently exists - dependencies are documented in README
- Uses standard library extensively (pathlib, typing, dataclasses)

### Running and Testing
```bash
# Install dependencies
pip install pandas openpyxl pyyaml

# Test basic functionality
./transform-myd-minimal --help
./transform-myd-minimal map --help

# Run with sample data (if available)
./transform-myd-minimal map -object m140 -variant bnka
```

### Key Configuration Files
- `config/config.yaml` - Application settings (fuzzy thresholds, paths)
- `config/central_mapping_memory.yaml` - Reusable mapping rules
- Input format: `data/02_fields/fields_{object}_{variant}.xlsx`

### Code Patterns to Follow

#### Type Hints
All functions should use comprehensive type hints:
```python
from typing import Dict, List, Optional, Tuple
from pathlib import Path

def process_fields(excel_path: Path, config: Dict[str, Any]) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Process Excel fields with proper typing."""
```

#### Dataclasses for Configuration
Use dataclasses for structured configuration:
```python
@dataclass
class MatchingConfig:
    threshold: float
    max_suggestions: int
    use_fuzzy: bool
```

#### Error Handling
Provide clear error messages with context:
```python
try:
    df = pd.read_excel(excel_path)
except FileNotFoundError:
    raise FileNotFoundError(f"Excel file not found: {excel_path}")
except Exception as e:
    raise Exception(f"Error reading Excel file: {e}")
```

#### Logging/Output Style
Use structured console output for user feedback:
```python
print("=== Advanced Matching Results ===")
print(f"Exact matches: {exact_count}")
print(f"Fuzzy matches: {fuzzy_count}")
print(f"Coverage: {coverage:.1f}%")
```

### Common Modification Patterns

#### Adding New Matching Algorithms
1. Add method to `FuzzyMatcher` class in `fuzzy.py`
2. Update `AdvancedFieldMatcher` in `main.py` to use new algorithm
3. Add configuration options in `config_loader.py`
4. Update CLI arguments in `cli.py`

#### Extending YAML Output
1. Modify generator functions in `generator.py`
2. Update data structures in `main.py` if needed
3. Test with sample data to ensure valid YAML

#### Adding New CLI Commands
1. Add subparser in `cli.py` setup_cli() function
2. Create handler function in appropriate module
3. Wire up in main() orchestration function

### File Naming Conventions
- Input: `fields_{object}_{variant}.xlsx`
- Legacy output: `config/{object}/{variant}/`
- New output: `migrations/{OBJECT}/{variant}/`
- Config files: `config/` directory

### Business Logic Understanding
- **Exact matching**: 100% confidence, normalized comparison
- **Synonym matching**: 85% confidence, business term equivalency
- **Fuzzy matching**: Variable confidence based on similarity score
- **Audit matching**: Tracks potential matches to already-mapped targets
- **Central memory**: Global rules that override automatic matching

### Performance Considerations
- Fuzzy matching can be disabled for large datasets (`--disable-fuzzy`)
- Threshold adjustment affects processing time vs. accuracy trade-off
- Excel file reading is the primary I/O bottleneck

### Debugging Tips
- Use `--max-suggestions 10` to see more potential matches
- Lower `--fuzzy-threshold` to understand why matches might be missed
- Check console output for detailed matching statistics
- Review generated YAML comments for audit information

### Testing Strategy
Since no formal test suite exists:
1. Test CLI help commands work correctly
2. Run with sample Excel files if available
3. Validate YAML output structure and content
4. Check console output for expected statistics
5. Verify both legacy and new output structures are generated

### Breaking Changes to Avoid
- Don't modify the Excel input file format expectations
- Maintain backward compatibility for legacy CLI format
- Keep existing YAML structure for legacy output
- Preserve existing configuration file format