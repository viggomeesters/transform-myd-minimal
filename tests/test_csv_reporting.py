#!/usr/bin/env python3
"""
Tests for CSV HTML reporting functionality integrated with transform command.
"""

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from transform_myd_minimal.csv_reporting import generate_csv_html_report


class TestCSVReporting(unittest.TestCase):
    """Test cases for CSV HTML reporting functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = Path(tempfile.mkdtemp())

        # Create a sample CSV file for testing
        self.sample_data = {
            "row_id": [1, 2, 3, 4, 5],
            "customer_id": ["C001", "C002", "", "C004", "C005"],
            "customer_name": [
                "John Smith",
                "",
                "Jane Doe",
                "Bob Wilson",
                "Alice Brown",
            ],
            "amount": [100.50, 250.00, 75.25, -50.00, 999.99],
            "currency": ["USD", "EUR", "GBP", "USD", ""],
            "status": ["REJECTED", "REJECTED", "REJECTED", "REJECTED", "REJECTED"],
            "error_message": [
                "Invalid currency format",
                "Missing customer name",
                "Missing customer ID",
                "Negative amount not allowed",
                "Currency field is required",
            ],
            "processed_date": [
                "2024-01-15",
                "2024-01-16",
                "2024-01-16",
                "2024-01-17",
                "2024-01-17",
            ],
        }

        self.csv_file = self.test_dir / "test_rejects.csv"
        df = pd.DataFrame(self.sample_data)
        df.to_csv(self.csv_file, index=False)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.test_dir)

    def test_generate_csv_html_report_basic(self):
        """Test basic HTML report generation from CSV for rejected records."""
        output_file = self.test_dir / "output.html"
        title = "Rejected Records Report · test/bnka"

        # Generate the report (this simulates what transform command does)
        generate_csv_html_report(self.csv_file, output_file, title)

        # Check that output file was created
        self.assertTrue(output_file.exists())

        # Read and verify content
        with open(output_file, encoding="utf-8") as f:
            content = f.read()

        # Check basic HTML structure
        self.assertIn("<!DOCTYPE html>", content)
        self.assertIn('<html lang="en">', content)
        self.assertIn("<title>Rejected Records Report · test/bnka</title>", content)
        self.assertIn(title, content)

        # Check that data is embedded as JSON
        self.assertIn('<script id="data" type="application/json">', content)

        # Check for key functionality
        self.assertIn("toggleTheme()", content)  # Dark mode toggle
        self.assertIn("applyFilters()", content)  # Filtering
        self.assertIn("sortTable(", content)  # Sorting
        self.assertIn("downloadFilteredCSV()", content)  # CSV export

        # Check for table structure
        self.assertIn('<table id="data-table">', content)
        self.assertIn("row_id", content)
        self.assertIn("customer_id", content)
        self.assertIn("error_message", content)

    def test_html_report_handles_nan_values(self):
        """Test that NaN values are properly handled in HTML report."""
        # Create CSV with explicit NaN values
        csv_with_nan = self.test_dir / "test_with_nan.csv"
        df = pd.DataFrame(
            {"col1": ["A", "", "C"], "col2": [1, None, 3], "col3": ["X", "Y", ""]}
        )
        df.to_csv(csv_with_nan, index=False)

        output_file = self.test_dir / "nan_output.html"
        generate_csv_html_report(csv_with_nan, output_file, "NaN Test")

        # Verify file was created
        self.assertTrue(output_file.exists())

        # Check content handles empty values properly
        with open(output_file, encoding="utf-8") as f:
            content = f.read()

        # Should contain the data but handle empty values
        self.assertIn('"col1"', content)
        self.assertIn('"col2"', content)
        self.assertIn('"col3"', content)

    def test_html_report_column_statistics(self):
        """Test that column statistics are properly calculated."""
        output_file = self.test_dir / "stats_output.html"
        generate_csv_html_report(self.csv_file, output_file, "Stats Test")

        with open(output_file, encoding="utf-8") as f:
            content = f.read()

        # Check that column statistics are included in the embedded data
        self.assertIn('"column_stats"', content)
        self.assertIn('"top_values"', content)

        # Should contain statistics for each column
        for col in self.sample_data:
            self.assertIn(f'"{col}"', content)

    def test_html_report_responsive_design(self):
        """Test that the HTML report includes responsive design elements."""
        output_file = self.test_dir / "responsive_output.html"
        generate_csv_html_report(self.csv_file, output_file, "Responsive Test")

        with open(output_file, encoding="utf-8") as f:
            content = f.read()

        # Check for responsive design elements
        self.assertIn("viewport", content)
        self.assertIn("grid-template-columns", content)
        self.assertIn("flex-wrap", content)

        # Check for mobile-friendly CSS
        self.assertIn("box-sizing: border-box", content)
        self.assertIn("overflow-x: auto", content)

    def test_html_report_css_variables(self):
        """Test that CSS variables are used for theming."""
        output_file = self.test_dir / "theme_output.html"
        generate_csv_html_report(self.csv_file, output_file, "Theme Test")

        with open(output_file, encoding="utf-8") as f:
            content = f.read()

        # Check for CSS custom properties (variables)
        self.assertIn(":root {", content)
        self.assertIn("--bg-color:", content)
        self.assertIn("--container-bg:", content)
        self.assertIn("--text-color:", content)
        self.assertIn('[data-theme="dark"]', content)

    def test_html_report_javascript_functionality(self):
        """Test that essential JavaScript functions are included."""
        output_file = self.test_dir / "js_output.html"
        generate_csv_html_report(self.csv_file, output_file, "JS Test")

        with open(output_file, encoding="utf-8") as f:
            content = f.read()

        # Check for essential JavaScript functions
        required_functions = [
            "initializeTable",
            "renderTableRows",
            "initializeFilters",
            "initializeColumnKPIs",
            "applyFilters",
            "updateVisibleRowsCount",
            "updateColumnKPIs",
            "sortTable",
            "downloadFilteredCSV",
            "toggleTheme",
        ]

        for func in required_functions:
            self.assertIn(f"function {func}(", content)

    def test_html_report_data_integrity(self):
        """Test that the original data is preserved in the HTML report."""
        output_file = self.test_dir / "integrity_output.html"
        generate_csv_html_report(self.csv_file, output_file, "Integrity Test")

        with open(output_file, encoding="utf-8") as f:
            content = f.read()

        # Check that all original data values are present
        self.assertIn("John Smith", content)
        self.assertIn("C001", content)
        self.assertIn("100.5", content)  # JSON numbers may not have trailing zero
        self.assertIn("Invalid currency format", content)
        self.assertIn("2024-01-15", content)

        # Check row and column counts - use more flexible matching
        self.assertIn('"total_rows":', content)
        self.assertIn('"total_columns":', content)

        # Extract and verify the JSON data more precisely
        import json
        import re

        json_match = re.search(
            r'<script id="data" type="application/json">(.*?)</script>',
            content,
            re.DOTALL,
        )
        self.assertIsNotNone(json_match, "JSON data should be embedded in the HTML")

        json_data = json.loads(json_match.group(1))
        self.assertEqual(json_data["total_rows"], 5)
        self.assertEqual(json_data["total_columns"], 8)

    def test_transform_integration_title_format(self):
        """Test that the title format matches what transform command uses."""
        output_file = self.test_dir / "transform_format.html"

        # Test the title format that transform command uses
        title = "Rejected Records Report · test/bnka"
        generate_csv_html_report(self.csv_file, output_file, title)

        with open(output_file, encoding="utf-8") as f:
            content = f.read()

        # Verify the title is properly embedded
        self.assertIn(title, content)
        self.assertIn("<title>Rejected Records Report · test/bnka</title>", content)


if __name__ == "__main__":
    unittest.main()
