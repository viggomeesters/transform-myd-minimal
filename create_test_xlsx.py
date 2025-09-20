#!/usr/bin/env python3
"""Create test XLSX files for testing error scenarios."""

import pandas as pd
from pathlib import Path

# Create test directory
test_dir = Path("data/01_source")
test_dir.mkdir(parents=True, exist_ok=True)

# Create an empty Excel file (no headers)
empty_df = pd.DataFrame()
empty_file = test_dir / "index_source_empty_test.xlsx"
empty_df.to_excel(empty_file, index=False)
print(f"Created empty test file: {empty_file}")

# Create an Excel file with only empty headers
empty_headers_df = pd.DataFrame({"": [""], " ": [""], "  ": [""]})
empty_headers_file = test_dir / "index_source_empty_headers_test.xlsx"
empty_headers_df.to_excel(empty_headers_file, index=False)
print(f"Created empty headers test file: {empty_headers_file}")

# Create a valid Excel file with headers for positive testing
valid_df = pd.DataFrame({
    "Field Name": ["field1", "field2", "field3"],
    "Description": ["desc1", "desc2", "desc3"],
    "Type": ["string", "int", "float"]
})
valid_file = test_dir / "index_source_valid_test.xlsx"
valid_df.to_excel(valid_file, index=False)
print(f"Created valid test file: {valid_file}")