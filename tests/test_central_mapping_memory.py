"""Tests for central mapping memory functionality."""

import pytest
from pathlib import Path
import tempfile
import yaml

from transform_myd_minimal.main import (
    apply_field_descriptions_from_central_memory,
    apply_central_memory_to_unmapped_fields,
    CentralMappingMemory,
    SkipRule,
    ManualMapping
)


def test_apply_field_descriptions_from_central_memory():
    """Test that field descriptions are applied from central mapping memory."""
    # Create test data
    source_fields = [
        {"field_name": "MANDT", "field_description": None, "example": "280"},
        {"field_name": "ERDAT", "field_description": None, "example": "20150714"},
        {"field_name": "UNKNOWN_FIELD", "field_description": None, "example": "test"}
    ]
    
    # Create central mapping memory with skip rules
    central_memory = CentralMappingMemory(
        global_skip_fields=[
            SkipRule(
                source_field="MANDT",
                source_description="Client (Mandant)",
                skip=True,
                comment="Audit field: Client is not relevant for data mapping"
            ),
            SkipRule(
                source_field="ERDAT", 
                source_description="Creation Date",
                skip=True,
                comment="Audit field: Creation date is not relevant for data mapping"
            )
        ],
        global_manual_mappings=[],
        table_specific={},
        synonyms={}
    )
    
    # Apply field descriptions
    enhanced_fields = apply_field_descriptions_from_central_memory(
        source_fields, central_memory, "m140", "bnka"
    )
    
    # Check results
    assert enhanced_fields[0]["field_description"] == "Client (Mandant)"
    assert enhanced_fields[1]["field_description"] == "Creation Date"
    assert enhanced_fields[2]["field_description"] is None  # No rule for this field


def test_apply_central_memory_to_unmapped_fields():
    """Test that unmapped fields are enhanced with central mapping memory context."""
    # Create test mapping result
    mapping_result = {
        "unmapped_source_fields": ["MANDT", "ERDAT", "UNKNOWN_FIELD"],
        "mappings": [],
        "to_audit": [],
        "unmapped_target_fields": [],
        "metadata": {}
    }
    
    # Create central mapping memory
    central_memory = CentralMappingMemory(
        global_skip_fields=[
            SkipRule(
                source_field="MANDT",
                source_description="Client (Mandant)",
                skip=True,
                comment="Audit field: Client is not relevant for data mapping"
            )
        ],
        global_manual_mappings=[],
        table_specific={},
        synonyms={}
    )
    
    # Apply central memory context
    enhanced_result = apply_central_memory_to_unmapped_fields(
        mapping_result, central_memory, "m140", "bnka"
    )
    
    # Check that MANDT is enhanced
    unmapped_fields = enhanced_result["unmapped_source_fields"]
    mandt_field = unmapped_fields[0]
    
    assert isinstance(mandt_field, dict)
    assert mandt_field["source_field_name"] == "MANDT"
    assert mandt_field["source_field_description"] == "Client (Mandant)"
    assert mandt_field["confidence"] == 1.0
    assert mandt_field["rationale"] == "Global skip field configured in central mapping memory"
    assert mandt_field["comment"] == "Audit field: Client is not relevant for data mapping"
    
    # Check that unknown field remains as string
    assert unmapped_fields[2] == "UNKNOWN_FIELD"


def test_no_central_memory():
    """Test that functions handle None central memory gracefully."""
    source_fields = [{"field_name": "MANDT", "field_description": None}]
    
    # Should return unchanged
    result = apply_field_descriptions_from_central_memory(
        source_fields, None, "m140", "bnka"
    )
    assert result == source_fields
    
    mapping_result = {"unmapped_source_fields": ["MANDT"]}
    result = apply_central_memory_to_unmapped_fields(
        mapping_result, None, "m140", "bnka"
    )
    assert result == mapping_result