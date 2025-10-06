#!/usr/bin/env python3
"""
Tests for data profiling functionality in HTML reports.
"""

import tempfile
from pathlib import Path

import pandas as pd

from transform_myd_minimal.reporting import (
    profile_dataframe,
    profile_series,
    write_html_report,
)


def test_profile_series_string():
    """Test profiling of string data."""
    data = pd.Series(["apple", "banana", "apple", "", "cherry", None, "  apple  "])
    profile = profile_series("test_field", data, "string")

    assert profile["field"] == "test_field"
    assert profile["type"] == "string"
    assert profile["count"] == 5  # Non-empty/non-null values
    assert profile["missing"] == 2  # Empty string + None
    assert (
        profile["unique"] == 4
    )  # apple, banana, cherry, "  apple  " (whitespace treated as separate)
    assert "length" in profile
    assert profile["length"]["min"] == 5  # "apple"
    assert profile["length"]["max"] == 9  # "  apple  "


def test_profile_series_numeric():
    """Test profiling of numeric data."""
    data = pd.Series(["1.5", "2.0", "invalid", "", "3.5", None])
    profile = profile_series("test_number", data, "decimal")

    assert profile["field"] == "test_number"
    assert profile["type"] == "decimal"
    assert profile["count"] == 4  # Non-empty values (including invalid)
    assert profile["invalid"] == 1  # "invalid" string
    assert profile["missing"] == 2  # Empty + None
    assert "numeric" in profile
    assert profile["numeric"]["min"] == 1.5
    assert profile["numeric"]["max"] == 3.5


def test_profile_series_date():
    """Test profiling of date data."""
    data = pd.Series(["20240101", "20240201", "invalid", "", "20240301"])
    profile = profile_series("test_date", data, "date")

    assert profile["field"] == "test_date"
    assert profile["type"] == "date"
    assert profile["count"] == 4  # Non-empty values
    assert profile["invalid"] == 1  # "invalid" string
    assert profile["missing"] == 1  # Empty string
    assert "date" in profile
    assert profile["date"]["min"] == "20240101"
    assert profile["date"]["max"] == "20240301"


def test_profile_series_time():
    """Test profiling of time data."""
    data = pd.Series(["093000", "120000", "invalid", "", "180000"])
    profile = profile_series("test_time", data, "time")

    assert profile["field"] == "test_time"
    assert profile["type"] == "time"
    assert profile["count"] == 4  # Non-empty values
    assert profile["invalid"] == 1  # "invalid" string
    assert profile["missing"] == 1  # Empty string
    assert "time" in profile
    assert profile["time"]["min"] == "093000"
    assert profile["time"]["max"] == "180000"


def test_profile_dataframe():
    """Test profiling of entire DataFrame."""
    df = pd.DataFrame(
        {
            "string_col": ["a", "b", "", "c"],
            "number_col": ["1", "2", "invalid", "4"],
            "date_col": ["20240101", "", "20240201", "20240301"],
        }
    )

    validation_rules = {"number_col": {"type": "int"}, "date_col": {"type": "date"}}

    profiles = profile_dataframe(df, validation_rules)

    assert len(profiles) == 3
    assert "string_col" in profiles
    assert "number_col" in profiles
    assert "date_col" in profiles

    # Check types were applied correctly
    assert profiles["string_col"]["type"] == "string"
    assert profiles["number_col"]["type"] == "int"
    assert profiles["date_col"]["type"] == "date"


def test_quality_score_calculation():
    """Test quality score calculation."""
    # Perfect data
    data = pd.Series(["a", "b", "c", "d", "e"])  # No missing, no invalid, all unique
    profile = profile_series("perfect", data, "string")
    assert profile["quality_score"] == 100.0

    # Data with missing values
    data = pd.Series(["a", "b", "", "", "e"])  # 40% missing
    profile = profile_series("missing", data, "string")
    assert profile["quality_score"] == 84.0  # 100 - (40 * 0.4) = 84

    # Data with duplicates
    data = pd.Series(["a", "a", "a", "a", "a"])  # 80% duplicates (unique_ratio = 0.2)
    profile = profile_series("duplicates", data, "string")
    assert profile["quality_score"] == 84.0  # 100 - (80 * 0.2) = 84


def test_html_report_with_profiling():
    """Test HTML report generation with field profiling data."""
    summary = {
        "step": "raw_validation",
        "object": "test",
        "variant": "test",
        "ts": "2024-01-01T00:00:00",
        "rows_in": 5,
        "field_profiles": {
            "test_field": {
                "field": "test_field",
                "type": "string",
                "count": 4,
                "missing": 1,
                "invalid": 0,
                "unique": 3,
                "quality_score": 92.0,
                "missing_pct": 20.0,
                "invalid_pct": 0.0,
                "unique_pct": 75.0,
                "top_values": [{"value": "test", "count": 2}],
                "histogram": {"bins": ["0-5", "5-10"], "counts": [2, 2]},
            }
        },
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        html_path = Path(tmpdir) / "test_profiling.html"
        write_html_report(summary, html_path, "Test Profiling Report")

        # Check that file was created
        assert html_path.exists()

        # Check content includes profiling elements
        html_content = html_path.read_text(encoding="utf-8")
        assert "Data Summary" in html_content
        assert "Field Profiles CSV" in html_content
        assert "Quality Score" in html_content
        assert "profiling-table" in html_content
        assert "renderDataProfiling" in html_content


def test_histogram_generation():
    """Test histogram generation for different data types."""
    # String length histogram
    data = pd.Series(["a", "bb", "ccc", "dddd", "eeeee"])
    profile = profile_series("test", data, "string")
    assert "histogram" in profile
    assert len(profile["histogram"]["bins"]) > 0

    # Numeric histogram
    data = pd.Series(["1", "2", "3", "4", "5"])
    profile = profile_series("test", data, "decimal")
    assert "histogram" in profile
    assert len(profile["histogram"]["bins"]) > 0


if __name__ == "__main__":
    print("Running data profiling tests...")

    test_profile_series_string()
    print("✓ String profiling test passed")

    test_profile_series_numeric()
    print("✓ Numeric profiling test passed")

    test_profile_series_date()
    print("✓ Date profiling test passed")

    test_profile_series_time()
    print("✓ Time profiling test passed")

    test_profile_dataframe()
    print("✓ DataFrame profiling test passed")

    test_quality_score_calculation()
    print("✓ Quality score calculation test passed")

    test_html_report_with_profiling()
    print("✓ HTML report with profiling test passed")

    test_histogram_generation()
    print("✓ Histogram generation test passed")

    print("All data profiling tests passed!")
