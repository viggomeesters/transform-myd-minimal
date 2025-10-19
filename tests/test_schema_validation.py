"""Tests for schema validation functionality."""

import pytest

from transform_myd_minimal.schema import (
    ValidationError,
    validate_central_mapping_memory,
    validate_config,
    validate_index_source,
    validate_index_target,
    validate_mapping,
)


class TestConfigValidation:
    """Tests for config.yaml validation."""

    def test_valid_minimal_config(self):
        """Test that a minimal valid config passes validation."""
        config_data = {
            "fuzzy_threshold": 0.6,
            "max_suggestions": 3,
            "disable_fuzzy": False,
            "input_dir": "data/01_source",
            "output_dir": "output",
        }
        result = validate_config(config_data)
        assert result.fuzzy_threshold == 0.6
        assert result.max_suggestions == 3

    def test_valid_full_config(self):
        """Test that a full valid config passes validation."""
        config_data = {
            "object": "m140",
            "variant": "bnka",
            "fuzzy_threshold": 0.8,
            "max_suggestions": 5,
            "disable_fuzzy": False,
            "input_dir": "data/01_source",
            "output_dir": "output",
            "mapping": {
                "from_sources": True,
                "source_headers": {
                    "path": "data/01_source/BNKA_headers.xlsx",
                    "sheet": "Sheet1",
                    "header_row": 1,
                    "ignore_data_below": True,
                },
                "target_xml": {
                    "path": "data/01_source/Source data for Bank.xml",
                    "worksheet_name": "Field List",
                    "header_match": {
                        "sheet_name": "Sheet Name",
                        "group_name": "Group Name",
                        "description": "Field Description",
                        "importance": "Importance",
                        "type": "Type",
                        "length": "Length",
                        "decimal": "Decimal",
                        "sap_table": "SAP Structure",
                        "sap_field": "SAP Field",
                    },
                    "normalization": {
                        "strip_table_prefix": "S_",
                        "uppercase_table_field": True,
                    },
                    "output_naming": {
                        "transformer_id_template": "{sap_table}#{sap_field}",
                        "internal_id_template": "{internal_table}.{sap_field}",
                    },
                },
            },
            "matching": {"target_label_priority": ["description", "sap_field"]},
        }
        result = validate_config(config_data)
        assert result.object == "m140"
        assert result.variant == "bnka"
        assert result.fuzzy_threshold == 0.8

    def test_invalid_fuzzy_threshold_too_high(self):
        """Test that fuzzy_threshold > 1.0 fails validation."""
        config_data = {
            "fuzzy_threshold": 1.5,
            "max_suggestions": 3,
            "disable_fuzzy": False,
            "input_dir": "data/01_source",
            "output_dir": "output",
        }
        with pytest.raises(ValidationError) as exc_info:
            validate_config(config_data)
        assert "fuzzy_threshold" in str(exc_info.value).lower()

    def test_invalid_fuzzy_threshold_negative(self):
        """Test that negative fuzzy_threshold fails validation."""
        config_data = {
            "fuzzy_threshold": -0.1,
            "max_suggestions": 3,
            "disable_fuzzy": False,
            "input_dir": "data/01_source",
            "output_dir": "output",
        }
        with pytest.raises(ValidationError) as exc_info:
            validate_config(config_data)
        assert "fuzzy_threshold" in str(exc_info.value).lower()

    def test_invalid_max_suggestions_zero(self):
        """Test that max_suggestions = 0 fails validation."""
        config_data = {
            "fuzzy_threshold": 0.6,
            "max_suggestions": 0,
            "disable_fuzzy": False,
            "input_dir": "data/01_source",
            "output_dir": "output",
        }
        with pytest.raises(ValidationError) as exc_info:
            validate_config(config_data)
        assert "max_suggestions" in str(exc_info.value).lower()

    def test_invalid_type_fuzzy_threshold(self):
        """Test that non-numeric fuzzy_threshold fails validation."""
        config_data = {
            "fuzzy_threshold": "not_a_number",
            "max_suggestions": 3,
            "disable_fuzzy": False,
            "input_dir": "data/01_source",
            "output_dir": "output",
        }
        with pytest.raises(ValidationError):
            validate_config(config_data)


class TestCentralMappingMemoryValidation:
    """Tests for central_mapping_memory.yaml validation."""

    def test_valid_minimal_central_memory(self):
        """Test that a minimal valid central mapping memory passes validation."""
        data = {
            "synonyms": {},
            "global_skip_fields": [],
            "global_manual_mappings": [],
            "table_specific": {},
        }
        result = validate_central_mapping_memory(data)
        assert result.synonyms == {}

    def test_valid_full_central_memory(self):
        """Test that a full valid central mapping memory passes validation."""
        data = {
            "synonyms": {
                "BANKL": ["Bank Key", "Bank Number", "Bank ID"],
                "BANKA": ["Bank Name", "Bank Title"],
            },
            "global_skip_fields": [
                {
                    "source_field": "MANDT",
                    "source_description": "Client (Mandant)",
                    "skip": True,
                    "comment": "Audit field: Client is not relevant",
                }
            ],
            "global_manual_mappings": [
                {
                    "source_field": "CLIENT_ID",
                    "source_description": "Client identifier",
                    "target": "MANDT",
                    "target_description": "Client (Mandant)",
                    "comment": "Standard mapping",
                }
            ],
            "table_specific": {
                "m140_bnka": {
                    "skip_fields": [
                        {
                            "source_field": "ZRES1",
                            "source_description": "Reserved field 1",
                            "skip": True,
                            "comment": "Reserved field not used",
                        }
                    ],
                    "manual_mappings": [
                        {
                            "source_field": "IBAN_RULE",
                            "source_description": "IBAN Validation Rule",
                            "target": "SWIFT",
                            "target_description": "SWIFT Code",
                            "comment": "Business rule mapping",
                        }
                    ],
                }
            },
        }
        result = validate_central_mapping_memory(data)
        assert len(result.global_skip_fields) == 1
        assert len(result.global_manual_mappings) == 1

    def test_invalid_skip_rule_missing_field(self):
        """Test that skip rule with missing required field fails validation."""
        data = {
            "global_skip_fields": [
                {
                    "source_field": "MANDT",
                    "skip": True,
                    "comment": "Audit field",
                    # Missing source_description
                }
            ]
        }
        with pytest.raises(ValidationError):
            validate_central_mapping_memory(data)

    def test_invalid_manual_mapping_missing_field(self):
        """Test that manual mapping with missing required field fails validation."""
        data = {
            "global_manual_mappings": [
                {
                    "source_field": "CLIENT_ID",
                    "source_description": "Client identifier",
                    "target": "MANDT",
                    # Missing target_description and comment
                }
            ]
        }
        with pytest.raises(ValidationError):
            validate_central_mapping_memory(data)

    def test_empty_central_memory(self):
        """Test that an empty central mapping memory is valid."""
        data = {}
        result = validate_central_mapping_memory(data)
        assert result.synonyms is None or result.synonyms == {}


class TestIndexSourceValidation:
    """Tests for index_source.yaml validation."""

    def test_valid_index_source(self):
        """Test that a valid index_source passes validation."""
        data = {
            "metadata": {
                "object": "m140",
                "variant": "bnka",
                "generated_at": "2025-09-26T09:28:53.347740",
            },
            "source_fields": [
                {
                    "source_field_name": "MANDT",
                    "source_field_description": "Client (Mandant)",
                    "source_example": None,
                    "source_field_count": 1,
                    "source_dtype": "string",
                    "source_nullable": False,
                },
                {
                    "source_field_name": "BANKL",
                    "source_field_description": "Bank Key",
                    "source_example": "12345",
                    "source_field_count": 2,
                    "source_dtype": "string",
                    "source_nullable": True,
                },
            ],
        }
        result = validate_index_source(data)
        assert result.metadata.object == "m140"
        assert len(result.source_fields) == 2

    def test_invalid_index_source_missing_metadata(self):
        """Test that index_source without metadata fails validation."""
        data = {
            "source_fields": [
                {"source_field_name": "MANDT", "source_field_description": "Client"}
            ]
        }
        with pytest.raises(ValidationError):
            validate_index_source(data)

    def test_invalid_index_source_empty_fields(self):
        """Test that index_source with empty source_fields fails validation."""
        data = {
            "metadata": {"object": "m140", "variant": "bnka"},
            "source_fields": [],
        }
        with pytest.raises(ValidationError) as exc_info:
            validate_index_source(data)
        assert "source_fields cannot be empty" in str(exc_info.value)

    def test_invalid_index_source_missing_field_name(self):
        """Test that source field without name fails validation."""
        data = {
            "metadata": {"object": "m140", "variant": "bnka"},
            "source_fields": [
                {
                    # Missing source_field_name
                    "source_field_description": "Client (Mandant)",
                }
            ],
        }
        with pytest.raises(ValidationError):
            validate_index_source(data)


class TestIndexTargetValidation:
    """Tests for index_target.yaml validation."""

    def test_valid_index_target(self):
        """Test that a valid index_target passes validation."""
        data = {
            "metadata": {
                "object": "m140",
                "variant": "bnka",
                "target_file": "data/02_target/m140_bnka.xml",
                "generated_at": "2025-09-26T06:53:38.214005",
                "structure": "S_BNKA",
                "target_fields_count": 2,
            },
            "target_fields": [
                {
                    "target_field_name": "BANKS",
                    "target_field_description": "Bank Country/Region Key",
                    "target_table": "bnka",
                    "target_is_mandatory": True,
                    "target_field_group": "key",
                    "target_is_key": True,
                    "target_sheet_name": "Field List",
                    "target_data_type": "Text",
                    "target_length": 80,
                    "target_decimal": None,
                    "target_field_count": 1,
                },
                {
                    "target_field_name": "BANKL",
                    "target_field_description": "Bank Key",
                    "target_table": "bnka",
                    "target_is_mandatory": True,
                    "target_field_group": "key",
                    "target_is_key": True,
                    "target_sheet_name": "Field List",
                    "target_data_type": "Text",
                    "target_length": 80,
                    "target_decimal": None,
                    "target_field_count": 2,
                },
            ],
        }
        result = validate_index_target(data)
        assert result.metadata.object == "m140"
        assert len(result.target_fields) == 2

    def test_invalid_index_target_empty_fields(self):
        """Test that index_target with empty target_fields fails validation."""
        data = {
            "metadata": {"object": "m140", "variant": "bnka"},
            "target_fields": [],
        }
        with pytest.raises(ValidationError) as exc_info:
            validate_index_target(data)
        assert "target_fields cannot be empty" in str(exc_info.value)

    def test_invalid_index_target_missing_field_name(self):
        """Test that target field without name fails validation."""
        data = {
            "metadata": {"object": "m140", "variant": "bnka"},
            "target_fields": [
                {
                    # Missing target_field_name
                    "target_field_description": "Bank Country/Region Key",
                    "target_table": "bnka",
                }
            ],
        }
        with pytest.raises(ValidationError):
            validate_index_target(data)


class TestMappingValidation:
    """Tests for mapping.yaml validation."""

    def test_valid_mapping(self):
        """Test that a valid mapping passes validation."""
        data = {
            "metadata": {
                "object": "m140",
                "variant": "bnka",
                "generated_at": "2025-10-06T11:47:02.299426",
                "source_index": "migrations/m140/bnka/index_source.yaml",
                "target_index": "migrations/m140/bnka/index_target.yaml",
                "mapped_count": 2,
                "unmapped_count": 0,
                "to_audit": 0,
                "unused_sources": 0,
                "unused_targets": 0,
            },
            "mappings": [
                {
                    "map_confidence": 1.0,
                    "map_rationale": "Exact field name match",
                    "map_status": "auto",
                    "source_field_description": "Bank Country",
                    "source_field_name": "BANKS",
                    "source_header": "BANKS",
                    "target_field_description": "Bank Country/Region Key",
                    "target_field_name": "BANKS",
                    "target_table": "bnka",
                },
                {
                    "map_confidence": 0.95,
                    "map_rationale": "Fuzzy match",
                    "map_status": "auto",
                    "source_field_description": "Bank Key",
                    "source_field_name": "BANKL",
                    "source_header": "BANKL",
                    "target_field_description": "Bank Key",
                    "target_field_name": "BANKL",
                    "target_table": "bnka",
                },
            ],
        }
        result = validate_mapping(data)
        assert result.metadata.object == "m140"
        assert len(result.mappings) == 2

    def test_invalid_mapping_confidence_too_high(self):
        """Test that map_confidence > 1.0 fails validation."""
        data = {
            "metadata": {"object": "m140", "variant": "bnka"},
            "mappings": [
                {
                    "map_confidence": 1.5,  # Invalid
                    "map_rationale": "Test",
                    "map_status": "auto",
                    "source_field_name": "BANKS",
                    "target_field_name": "BANKS",
                }
            ],
        }
        with pytest.raises(ValidationError) as exc_info:
            validate_mapping(data)
        assert "map_confidence" in str(exc_info.value).lower()

    def test_invalid_mapping_confidence_negative(self):
        """Test that negative map_confidence fails validation."""
        data = {
            "metadata": {"object": "m140", "variant": "bnka"},
            "mappings": [
                {
                    "map_confidence": -0.1,  # Invalid
                    "map_rationale": "Test",
                    "map_status": "auto",
                    "source_field_name": "BANKS",
                    "target_field_name": "BANKS",
                }
            ],
        }
        with pytest.raises(ValidationError) as exc_info:
            validate_mapping(data)
        assert "map_confidence" in str(exc_info.value).lower()

    def test_valid_mapping_without_mappings_list(self):
        """Test that mapping without mappings list is valid (empty mapping)."""
        data = {
            "metadata": {
                "object": "m140",
                "variant": "bnka",
                "mapped_count": 0,
            }
        }
        result = validate_mapping(data)
        assert result.mappings is None or result.mappings == []

    def test_valid_mapping_with_skipped_and_unmapped(self):
        """Test that mapping with skipped and unmapped fields is valid."""
        data = {
            "metadata": {"object": "m140", "variant": "bnka"},
            "mappings": [],
            "skipped": [{"source_field_name": "MANDT", "comment": "Skipped"}],
            "unmapped_sources": [
                {"source_field_name": "UNKNOWN", "source_field_description": "Unknown"}
            ],
            "unmapped_targets": [
                {"target_field_name": "UNUSED", "target_field_description": "Unused"}
            ],
        }
        result = validate_mapping(data)
        assert result.skipped is not None
        assert result.unmapped_sources is not None
        assert result.unmapped_targets is not None
