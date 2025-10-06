#!/usr/bin/env python3
"""
Test-driven mapping system for transform-myd-minimal.

Allows users to define mapping test cases (source values -> expected target values)
and automatically tests mapping logic.
"""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest
import yaml

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class MappingTestCase:
    """Represents a single mapping test case."""

    def __init__(
        self,
        name: str,
        source_field: str,
        target_field: str,
        source_value: Any,
        expected_value: Any,
        transformation: str = "copy",
        description: str = "",
    ):
        """Initialize a mapping test case.

        Args:
            name: Name of the test case
            source_field: Source field name
            target_field: Target field name
            source_value: Input value from source
            expected_value: Expected output value in target
            transformation: Transformation type to apply
            description: Optional description of the test case
        """
        self.name = name
        self.source_field = source_field
        self.target_field = target_field
        self.source_value = source_value
        self.expected_value = expected_value
        self.transformation = transformation
        self.description = description

    def __repr__(self) -> str:
        return (
            f"MappingTestCase(name={self.name}, "
            f"source={self.source_field}, target={self.target_field})"
        )


class MappingTransformer:
    """Applies transformations to values based on mapping rules."""

    def apply_transformation(
        self,
        value: Any,
        transformation: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Apply a transformation to a value.

        Args:
            value: Input value
            transformation: Transformation type
            config: Optional configuration for the transformation

        Returns:
            Transformed value
        """
        config = config or {}

        if transformation == "copy":
            return value

        elif transformation == "constant":
            return config.get("constant_value", "")

        elif transformation == "derive":
            # Derived transformations need custom logic
            # For testing, we return a placeholder
            return f"DERIVED({value})"

        elif transformation == "lookup":
            # Lookup transformation uses a mapping table
            lookup_table = config.get("lookup_table", {})
            return lookup_table.get(str(value), value)

        elif transformation == "concatenate":
            # Concatenate multiple values
            values = config.get("values", [value])
            separator = config.get("separator", " ")
            return separator.join(str(v) for v in values)

        elif transformation == "split":
            # Split a value by delimiter
            delimiter = config.get("delimiter", " ")
            index = config.get("index", 0)
            parts = str(value).split(delimiter)
            return parts[index] if 0 <= index < len(parts) else ""

        elif transformation == "transform":
            # Custom transformation function
            transform_func = config.get("transform_func")
            if transform_func and callable(transform_func):
                return transform_func(value)
            return value

        else:
            # Unknown transformation, return value as-is
            return value


def load_test_cases_from_yaml(yaml_path: Path) -> List[MappingTestCase]:
    """Load mapping test cases from a YAML file.

    Args:
        yaml_path: Path to the YAML file containing test cases

    Returns:
        List of MappingTestCase objects
    """
    with open(yaml_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    test_cases = []
    for tc_data in data.get("test_cases", []):
        test_case = MappingTestCase(
            name=tc_data.get("name", ""),
            source_field=tc_data.get("source_field", ""),
            target_field=tc_data.get("target_field", ""),
            source_value=tc_data.get("source_value"),
            expected_value=tc_data.get("expected_value"),
            transformation=tc_data.get("transformation", "copy"),
            description=tc_data.get("description", ""),
        )
        test_cases.append(test_case)

    return test_cases


def run_test_case(
    test_case: MappingTestCase,
    transformer: MappingTransformer,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Run a single mapping test case.

    Args:
        test_case: Test case to run
        transformer: Transformer to use
        config: Optional transformation configuration

    Returns:
        Dictionary with test results
    """
    try:
        actual_value = transformer.apply_transformation(
            test_case.source_value,
            test_case.transformation,
            config,
        )

        passed = actual_value == test_case.expected_value

        return {
            "name": test_case.name,
            "passed": passed,
            "source_field": test_case.source_field,
            "target_field": test_case.target_field,
            "source_value": test_case.source_value,
            "expected_value": test_case.expected_value,
            "actual_value": actual_value,
            "transformation": test_case.transformation,
            "description": test_case.description,
        }

    except Exception as e:
        return {
            "name": test_case.name,
            "passed": False,
            "source_field": test_case.source_field,
            "target_field": test_case.target_field,
            "source_value": test_case.source_value,
            "expected_value": test_case.expected_value,
            "actual_value": None,
            "transformation": test_case.transformation,
            "description": test_case.description,
            "error": str(e),
        }


# Pytest fixtures and tests
@pytest.fixture
def transformer():
    """Fixture providing a MappingTransformer instance."""
    return MappingTransformer()


@pytest.fixture
def sample_test_cases():
    """Fixture providing sample test cases."""
    return [
        MappingTestCase(
            name="test_copy_transformation",
            source_field="BANK_NAME",
            target_field="BANKL",
            source_value="Deutsche Bank",
            expected_value="Deutsche Bank",
            transformation="copy",
            description="Simple copy transformation",
        ),
        MappingTestCase(
            name="test_constant_transformation",
            source_field="COUNTRY",
            target_field="BUKRS",
            source_value="Germany",
            expected_value="1000",
            transformation="constant",
            description="Constant value transformation",
        ),
        MappingTestCase(
            name="test_lookup_transformation",
            source_field="COUNTRY_CODE",
            target_field="LAND1",
            source_value="DE",
            expected_value="Germany",
            transformation="lookup",
            description="Lookup transformation from code to name",
        ),
    ]


def test_copy_transformation(transformer):
    """Test copy transformation (identity)."""
    test_case = MappingTestCase(
        name="test_copy",
        source_field="TEST_SOURCE",
        target_field="TEST_TARGET",
        source_value="test_value",
        expected_value="test_value",
        transformation="copy",
    )

    result = run_test_case(test_case, transformer)
    assert result["passed"], f"Copy transformation failed: {result}"


def test_constant_transformation(transformer):
    """Test constant transformation."""
    config = {"constant_value": "FIXED_VALUE"}

    test_case = MappingTestCase(
        name="test_constant",
        source_field="TEST_SOURCE",
        target_field="TEST_TARGET",
        source_value="any_value",
        expected_value="FIXED_VALUE",
        transformation="constant",
    )

    result = run_test_case(test_case, transformer, config)
    assert result["passed"], f"Constant transformation failed: {result}"


def test_lookup_transformation(transformer):
    """Test lookup transformation."""
    config = {
        "lookup_table": {
            "DE": "Germany",
            "FR": "France",
            "US": "United States",
        }
    }

    test_case = MappingTestCase(
        name="test_lookup",
        source_field="COUNTRY_CODE",
        target_field="COUNTRY_NAME",
        source_value="DE",
        expected_value="Germany",
        transformation="lookup",
    )

    result = run_test_case(test_case, transformer, config)
    assert result["passed"], f"Lookup transformation failed: {result}"


def test_concatenate_transformation(transformer):
    """Test concatenate transformation."""
    config = {
        "values": ["John", "Doe"],
        "separator": " ",
    }

    test_case = MappingTestCase(
        name="test_concatenate",
        source_field="NAMES",
        target_field="FULL_NAME",
        source_value="John",  # Will be overridden by config values
        expected_value="John Doe",
        transformation="concatenate",
    )

    result = run_test_case(test_case, transformer, config)
    assert result["passed"], f"Concatenate transformation failed: {result}"


def test_split_transformation(transformer):
    """Test split transformation."""
    config = {
        "delimiter": ",",
        "index": 0,
    }

    test_case = MappingTestCase(
        name="test_split",
        source_field="CSV_DATA",
        target_field="FIRST_VALUE",
        source_value="value1,value2,value3",
        expected_value="value1",
        transformation="split",
    )

    result = run_test_case(test_case, transformer, config)
    assert result["passed"], f"Split transformation failed: {result}"


def test_multiple_test_cases(transformer, sample_test_cases):
    """Test running multiple test cases."""
    results = []

    # Define configs for each test case
    configs = {
        "test_constant_transformation": {"constant_value": "1000"},
        "test_lookup_transformation": {
            "lookup_table": {"DE": "Germany", "US": "United States"}
        },
    }

    for test_case in sample_test_cases:
        config = configs.get(test_case.name, {})
        result = run_test_case(test_case, transformer, config)
        results.append(result)

    # Check that at least some tests passed
    passed_count = sum(1 for r in results if r["passed"])
    assert passed_count > 0, "No test cases passed"


# Command-line interface for running tests
def main():
    """Main entry point for command-line execution."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Run mapping test cases from a YAML file"
    )
    parser.add_argument(
        "--test-file",
        required=True,
        help="Path to YAML file containing test cases",
    )
    parser.add_argument(
        "--output",
        help="Optional output file for results (JSON format)",
    )
    parser.add_argument(
        "--html-report",
        help="Optional HTML report file",
    )

    args = parser.parse_args()

    test_file_path = Path(args.test_file)
    if not test_file_path.exists():
        print(f"Error: Test file not found: {test_file_path}", file=sys.stderr)
        sys.exit(1)

    # Load test cases
    print(f"Loading test cases from {test_file_path}...")
    test_cases = load_test_cases_from_yaml(test_file_path)
    print(f"Loaded {len(test_cases)} test cases\n")

    # Run tests
    transformer = MappingTransformer()
    results = []

    for test_case in test_cases:
        result = run_test_case(test_case, transformer)
        results.append(result)

        # Print result
        status = "✅ PASS" if result["passed"] else "❌ FAIL"
        print(f"{status} - {result['name']}")
        print(f"  Source: {result['source_field']} = {result['source_value']}")
        print(f"  Target: {result['target_field']}")
        print(f"  Expected: {result['expected_value']}")
        print(f"  Actual: {result['actual_value']}")
        if "error" in result:
            print(f"  Error: {result['error']}")
        print()

    # Summary
    passed_count = sum(1 for r in results if r["passed"])
    failed_count = len(results) - passed_count

    print("=" * 60)
    print(f"Test Summary: {passed_count} passed, {failed_count} failed")
    print("=" * 60)

    # Save results if requested
    if args.output:
        import json

        output_path = Path(args.output)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "summary": {
                        "total": len(results),
                        "passed": passed_count,
                        "failed": failed_count,
                    },
                    "results": results,
                },
                f,
                indent=2,
            )
        print(f"\nResults saved to: {output_path}")

    # Generate HTML report if requested
    if args.html_report:
        html_content = generate_html_report(results)
        html_path = Path(args.html_report)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"HTML report saved to: {html_path}")

    # Exit with error code if any tests failed
    sys.exit(0 if failed_count == 0 else 1)


def generate_html_report(results: List[Dict[str, Any]]) -> str:
    """Generate an HTML report from test results.

    Args:
        results: List of test result dictionaries

    Returns:
        HTML string
    """
    passed_count = sum(1 for r in results if r["passed"])
    failed_count = len(results) - passed_count

    rows_html = []
    for result in results:
        status_class = "pass" if result["passed"] else "fail"
        status_text = "✅ PASS" if result["passed"] else "❌ FAIL"

        rows_html.append(
            f"""
        <tr class="{status_class}">
            <td>{result['name']}</td>
            <td>{result['source_field']}</td>
            <td>{result['target_field']}</td>
            <td>{result['transformation']}</td>
            <td>{result['source_value']}</td>
            <td>{result['expected_value']}</td>
            <td>{result['actual_value']}</td>
            <td class="status">{status_text}</td>
        </tr>
        """
        )

    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Mapping Test Results</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                margin: 20px;
                background-color: #f5f5f5;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                padding: 30px;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            h1 {{
                color: #333;
                border-bottom: 2px solid #4472C4;
                padding-bottom: 10px;
            }}
            .summary {{
                display: flex;
                gap: 20px;
                margin: 20px 0;
            }}
            .metric {{
                padding: 15px 25px;
                border-radius: 5px;
                flex: 1;
                text-align: center;
            }}
            .metric.total {{
                background: #e7f3ff;
                border: 2px solid #4472C4;
            }}
            .metric.passed {{
                background: #d4edda;
                border: 2px solid #28a745;
            }}
            .metric.failed {{
                background: #f8d7da;
                border: 2px solid #dc3545;
            }}
            .metric-value {{
                font-size: 32px;
                font-weight: bold;
                margin-bottom: 5px;
            }}
            .metric-label {{
                font-size: 14px;
                color: #666;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
            }}
            th, td {{
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #ddd;
            }}
            th {{
                background-color: #4472C4;
                color: white;
                font-weight: bold;
            }}
            tr.pass {{
                background-color: #f0f9f0;
            }}
            tr.fail {{
                background-color: #fff5f5;
            }}
            tr:hover {{
                background-color: #f5f5f5;
            }}
            .status {{
                font-weight: bold;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🧪 Mapping Test Results</h1>
            
            <div class="summary">
                <div class="metric total">
                    <div class="metric-value">{len(results)}</div>
                    <div class="metric-label">Total Tests</div>
                </div>
                <div class="metric passed">
                    <div class="metric-value">{passed_count}</div>
                    <div class="metric-label">Passed</div>
                </div>
                <div class="metric failed">
                    <div class="metric-value">{failed_count}</div>
                    <div class="metric-label">Failed</div>
                </div>
            </div>
            
            <table>
                <thead>
                    <tr>
                        <th>Test Name</th>
                        <th>Source Field</th>
                        <th>Target Field</th>
                        <th>Transformation</th>
                        <th>Source Value</th>
                        <th>Expected</th>
                        <th>Actual</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rows_html)}
                </tbody>
            </table>
        </div>
    </body>
    </html>
    """

    return html


if __name__ == "__main__":
    # Check if running via pytest or command line
    if len(sys.argv) > 1 and sys.argv[1] not in ["-h", "--help", "--test-file"]:
        # Running via pytest
        pytest.main([__file__] + sys.argv[1:])
    elif "--test-file" in sys.argv:
        # Running via command line
        main()
    else:
        # Show help
        print("Usage:")
        print("  pytest tests/test_mapping.py              # Run pytest tests")
        print("  python tests/test_mapping.py --test-file <file>  # Run test cases from YAML")
