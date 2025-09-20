#!/usr/bin/env python3
"""Create a truly malformed Excel file that will cause an exception during analysis."""

import pandas as pd
from pathlib import Path

# Create a valid Excel file but with data that will cause analysis issues
# This should pass header detection but fail during column analysis
df = pd.DataFrame({
    "header1": ["", "", ""],  # All empty data
    "header2": ["", "", ""]
})

# Save to create a file that will pass initial checks but fail in analysis
test_file = Path("data/01_source/index_source_analysis_error_test.xlsx")
test_file.parent.mkdir(parents=True, exist_ok=True)

df.to_excel(test_file, index=False)
print(f"Created analysis error test file: {test_file}")

# Let's also test by creating an Excel file with headers but then corrupting it slightly
with open(test_file, "rb") as f:
    content = f.read()

# Write a corrupted version by truncating the file
corrupted_file = Path("data/01_source/index_source_corrupted_test.xlsx")
with open(corrupted_file, "wb") as f:
    f.write(content[:len(content)//2])  # Write only half the file
print(f"Created corrupted test file: {corrupted_file}")