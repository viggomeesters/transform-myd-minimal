#!/usr/bin/env python3
"""
Tests for HTML reporting functionality.
"""

import json
import tempfile
from pathlib import Path

from transform_myd_minimal.reporting import write_html_report, ensure_json_serializable


def test_ensure_json_serializable():
    """Test that ensure_json_serializable handles various data types."""
    # Test basic types
    assert ensure_json_serializable("string") == "string"
    assert ensure_json_serializable(123) == 123
    assert ensure_json_serializable(12.34) == 12.34
    assert ensure_json_serializable(True) == True
    assert ensure_json_serializable(None) == None
    
    # Test Path objects
    path_obj = Path("/some/path")
    assert ensure_json_serializable(path_obj) == "/some/path"
    
    # Test nested structures
    nested = {
        "path": Path("/test"),
        "list": [Path("/item1"), "string", 123],
        "dict": {"nested_path": Path("/nested")}
    }
    result = ensure_json_serializable(nested)
    assert result["path"] == "/test"
    assert result["list"] == ["/item1", "string", 123]
    assert result["dict"]["nested_path"] == "/nested"


def test_write_html_report_f01():
    """Test HTML report generation for F01 index_source."""
    summary = {
        "step": "index_source",
        "object": "m140",
        "variant": "bnka",
        "ts": "2025-09-23T04:00:00",
        "input_file": "data/01_source/m140_bnka.xlsx",
        "sheet": "Sheet1",
        "total_columns": 6,
        "headers": [
            {"index": 1, "field_name": "Bank Country", "dtype": "string", "nullable": True, "example": "US"},
            {"index": 2, "field_name": "Bank Name", "dtype": "string", "nullable": True, "example": "Chase"}
        ],
        "duplicates": [],
        "empty_headers": 1,
        "warnings": ["Empty header found"]
    }
    
    with tempfile.TemporaryDirectory() as tmpdir:
        html_path = Path(tmpdir) / "test_report.html"
        write_html_report(summary, html_path, "Test F01 Report")
        
        # Check that file was created
        assert html_path.exists()
        
        # Check content
        html_content = html_path.read_text(encoding='utf-8')
        assert "Test F01 Report" in html_content
        assert "index_source" in html_content
        assert "Bank Country" in html_content
        assert "Bank Name" in html_content
        assert 'id="data"' in html_content  # JSON embedding
        assert "downloadCSV" in html_content  # CSV download functionality


def test_write_html_report_f02():
    """Test HTML report generation for F02 index_target."""
    summary = {
        "step": "index_target",
        "object": "m140",
        "variant": "bnka", 
        "structure": "S_BNKA",
        "ts": "2025-09-23T04:00:00",
        "input_file": "data/02_target/m140_bnka.xml",
        "total_fields": 10,
        "mandatory": 6,
        "keys": 6,
        "groups": {"key": 6, "control data": 4},
        "order_ok": False,
        "sample_fields": [
            {"sap_field": "bukrs", "sap_table": "bnka", "mandatory": True, "key": True, "data_type": "Text", "length": 4}
        ],
        "anomalies": [],
        "validation_scaffold": {"created": True, "path": "migrations/m140/bnka/validation.yaml", "rules_count": 10},
        "warnings": []
    }
    
    with tempfile.TemporaryDirectory() as tmpdir:
        html_path = Path(tmpdir) / "test_f02_report.html"
        write_html_report(summary, html_path, "Test F02 Report")
        
        # Check that file was created
        assert html_path.exists()
        
        # Check content
        html_content = html_path.read_text(encoding='utf-8')
        assert "Test F02 Report" in html_content
        assert "index_target" in html_content
        assert "S_BNKA" in html_content
        assert "bukrs" in html_content


def test_write_html_report_f03():
    """Test HTML report generation for F03 map."""
    summary = {
        "step": "map",
        "object": "m140",
        "variant": "bnka",
        "ts": "2025-09-23T04:00:00",
        "source_index": "migrations/m140/bnka/index_source.yaml",
        "target_index": "migrations/m140/bnka/index_target.yaml",
        "mapped": 6,
        "unmapped": 4,
        "to_audit": 2,
        "unused_sources": 1,
        "mappings": [
            {"target_field": "BANKS", "source_header": "Bank Country", "required": True, "confidence": 0.95, "status": "auto", "rationale": "exact match"}
        ],
        "to_audit_rows": [],
        "unmapped_source_fields": ["Unused Field"],
        "unmapped_target_fields": [{"target_field": "BUKRS", "required": True}],
        "warnings": []
    }
    
    with tempfile.TemporaryDirectory() as tmpdir:
        html_path = Path(tmpdir) / "test_f03_report.html"
        write_html_report(summary, html_path, "Test F03 Report")
        
        # Check that file was created
        assert html_path.exists()
        
        # Check content
        html_content = html_path.read_text(encoding='utf-8')
        assert "Test F03 Report" in html_content
        assert "BANKS" in html_content
        assert "Bank Country" in html_content
        assert "exact match" in html_content


def test_write_html_report_f04_raw():
    """Test HTML report generation for F04 RAW validation."""
    summary = {
        "step": "raw_validation",
        "object": "m140",
        "variant": "bnka",
        "ts": "2025-09-23T04:00:00",
        "rows_in": 100,
        "null_rate_by_source": {"Bank Country": 0.15, "Swift Code": 0.20},
        "missing_sources": ["Required Field"],
        "warnings": []
    }
    
    with tempfile.TemporaryDirectory() as tmpdir:
        html_path = Path(tmpdir) / "test_f04_raw_report.html"
        write_html_report(summary, html_path, "Test F04 RAW Report")
        
        # Check that file was created
        assert html_path.exists()
        
        # Check content
        html_content = html_path.read_text(encoding='utf-8')
        assert "Test F04 RAW Report" in html_content
        assert "raw_validation" in html_content
        assert "Bank Country" in html_content
        assert "Required Field" in html_content


def test_write_html_report_f04_post():
    """Test HTML report generation for F04 POST validation."""
    summary = {
        "step": "post_transform_validation",
        "object": "m140",
        "variant": "bnka",
        "structure": "S_BNKA",
        "ts": "2025-09-23T04:00:00",
        "rows_in": 100,
        "rows_out": 90,
        "rows_rejected": 10,
        "mapped_coverage": 0.85,
        "template_used": "data/03_templates/S_BNKA#template.csv",
        "ignored_targets": [],
        "errors_by_rule": {"BUKRS.required": 5, "BANKS.max_length": 3},
        "errors_by_field": {"BUKRS": 5, "BANKS": 3},
        "sample_rows": [{"__rownum": 1, "BUKRS": "", "BANKS": "Test", "errors": ["BUKRS.required"]}],
        "warnings": []
    }
    
    with tempfile.TemporaryDirectory() as tmpdir:
        html_path = Path(tmpdir) / "test_f04_post_report.html"
        write_html_report(summary, html_path, "Test F04 POST Report")
        
        # Check that file was created
        assert html_path.exists()
        
        # Check content
        html_content = html_path.read_text(encoding='utf-8')
        assert "Test F04 POST Report" in html_content
        assert "post_transform_validation" in html_content
        assert "S_BNKA" in html_content
        assert "BUKRS.required" in html_content
        assert "CSV Export Requirements" in html_content  # Should show CSV requirements


def test_json_escaping():
    """Test that JSON with </script> tags is properly escaped."""
    summary = {
        "step": "test",
        "malicious_content": "Some </script><script>alert('xss')</script> content"
    }
    
    with tempfile.TemporaryDirectory() as tmpdir:
        html_path = Path(tmpdir) / "test_escaping.html"
        write_html_report(summary, html_path, "Test Escaping")
        
        html_content = html_path.read_text(encoding='utf-8')
        # Should not contain the literal </script> that would break embedding
        assert "</script><script>" not in html_content
        # Should contain the escaped version
        assert "</scr\" + \"ipt>" in html_content


if __name__ == "__main__":
    print("Running HTML reporting tests...")
    
    test_ensure_json_serializable()
    print("✓ ensure_json_serializable test passed")
    
    test_write_html_report_f01()
    print("✓ F01 HTML report test passed")
    
    test_write_html_report_f02()
    print("✓ F02 HTML report test passed")
    
    test_write_html_report_f03()
    print("✓ F03 HTML report test passed")
    
    test_write_html_report_f04_raw()
    print("✓ F04 RAW HTML report test passed")
    
    test_write_html_report_f04_post()
    print("✓ F04 POST HTML report test passed")
    
    test_json_escaping()
    print("✓ JSON escaping test passed")
    
    print("All HTML reporting tests passed!")