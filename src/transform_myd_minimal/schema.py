#!/usr/bin/env python3
"""
Schema validation for YAML and JSON config and output files.

This module provides Pydantic models for validating:
- config.yaml: Main configuration file
- central_mapping_memory.yaml: Central mapping memory configuration
- index_source.yaml: Source field index
- index_target.yaml: Target field index
- mapping.yaml: Field mapping results
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ValidationError(Exception):
    """Custom validation error for clearer error messages."""

    pass


# Config.yaml schemas
class SourceHeadersConfig(BaseModel):
    """Configuration for source headers."""

    path: str
    sheet: str
    header_row: int
    ignore_data_below: bool


class HeaderMatchConfig(BaseModel):
    """Configuration for header matching."""

    sheet_name: str
    group_name: str
    description: str
    importance: str
    type: str
    length: str
    decimal: str
    sap_table: str
    sap_field: str


class NormalizationConfig(BaseModel):
    """Configuration for normalization."""

    strip_table_prefix: str
    uppercase_table_field: bool


class OutputNamingConfig(BaseModel):
    """Configuration for output naming."""

    transformer_id_template: str
    internal_id_template: str


class TargetXmlConfig(BaseModel):
    """Configuration for target XML."""

    path: str
    worksheet_name: str
    header_match: HeaderMatchConfig
    normalization: NormalizationConfig
    output_naming: OutputNamingConfig


class MappingConfig(BaseModel):
    """Configuration for mapping."""

    from_sources: bool
    source_headers: SourceHeadersConfig | None = None
    target_xml: TargetXmlConfig | None = None


class MatchingConfig(BaseModel):
    """Configuration for matching."""

    target_label_priority: list[str]


class ConfigSchema(BaseModel):
    """Schema for config.yaml."""

    object: str | None = None
    variant: str | None = None
    fuzzy_threshold: float = Field(default=0.6, ge=0.0, le=1.0)
    max_suggestions: int = Field(default=3, ge=1)
    disable_fuzzy: bool = False
    input_dir: str = "data/01_source"
    output_dir: str = "output"
    mapping: MappingConfig | None = None
    matching: MatchingConfig | None = None

    @field_validator("fuzzy_threshold")
    @classmethod
    def validate_fuzzy_threshold(cls, v: float) -> float:
        """Validate fuzzy threshold is between 0 and 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("fuzzy_threshold must be between 0.0 and 1.0")
        return v


# Central mapping memory schemas
class SkipRuleSchema(BaseModel):
    """Schema for skip rule."""

    source_field: str
    source_description: str
    skip: bool
    comment: str


class ManualMappingSchema(BaseModel):
    """Schema for manual mapping."""

    source_field: str
    source_description: str
    target: str
    target_description: str
    comment: str


class TableSpecificRulesSchema(BaseModel):
    """Schema for table-specific rules."""

    skip_fields: list[SkipRuleSchema] | None = None
    manual_mappings: list[ManualMappingSchema] | None = None


class CentralMappingMemorySchema(BaseModel):
    """Schema for central_mapping_memory.yaml."""

    synonyms: dict[str, list[str]] | None = None
    global_skip_fields: list[SkipRuleSchema] | None = None
    global_manual_mappings: list[ManualMappingSchema] | None = None
    table_specific: dict[str, TableSpecificRulesSchema] | None = None


# Output file schemas
class MetadataSchema(BaseModel):
    """Schema for metadata section in output files."""

    object: str
    variant: str
    generated_at: str | datetime | None = None

    @field_validator("generated_at", mode="before")
    @classmethod
    def validate_generated_at(cls, v: Any) -> Any:
        """Allow string or datetime for generated_at field."""
        if v is None or isinstance(v, (str, datetime)):
            return v
        raise ValueError("generated_at must be a string or datetime")


class SourceFieldSchema(BaseModel):
    """Schema for source field in index_source.yaml."""

    source_field_name: str
    source_field_description: str | None = None
    source_example: Any | None = None
    source_field_count: int | None = None
    source_dtype: str | None = None
    source_nullable: bool | None = None


class IndexSourceSchema(BaseModel):
    """Schema for index_source.yaml."""

    metadata: MetadataSchema
    source_fields: list[SourceFieldSchema]

    @field_validator("source_fields")
    @classmethod
    def validate_source_fields(cls, v: list[SourceFieldSchema]) -> list[SourceFieldSchema]:
        """Validate that source_fields is not empty."""
        if not v:
            raise ValueError("source_fields cannot be empty")
        return v


class TargetFieldSchema(BaseModel):
    """Schema for target field in index_target.yaml."""

    target_field_name: str
    target_field_description: str | None = None
    target_table: str | None = None
    target_is_mandatory: bool | None = None
    target_field_group: str | None = None
    target_is_key: bool | None = None
    target_sheet_name: str | None = None
    target_data_type: str | None = None
    target_length: int | str | None = None
    target_decimal: int | str | None | None = None
    target_field_count: int | None = None


class TargetMetadataSchema(MetadataSchema):
    """Extended metadata for index_target.yaml."""

    target_file: str | None = None
    structure: str | None = None
    target_fields_count: int | None = None


class IndexTargetSchema(BaseModel):
    """Schema for index_target.yaml."""

    metadata: TargetMetadataSchema
    target_fields: list[TargetFieldSchema]

    @field_validator("target_fields")
    @classmethod
    def validate_target_fields(cls, v: list[TargetFieldSchema]) -> list[TargetFieldSchema]:
        """Validate that target_fields is not empty."""
        if not v:
            raise ValueError("target_fields cannot be empty")
        return v


class MappingFieldSchema(BaseModel):
    """Schema for mapping field in mapping.yaml."""

    source_field_name: str | None = None
    source_field_description: str | None = None
    source_header: str | None = None
    target_field_name: str | None = None
    target_field_description: str | None = None
    target_table: str | None = None
    map_confidence: float | None = None
    map_rationale: str | None = None
    map_status: str | None = None
    comment: str | None = None

    @field_validator("map_confidence")
    @classmethod
    def validate_map_confidence(cls, v: float | None) -> float | None:
        """Validate map_confidence is between 0 and 1."""
        if v is not None and not 0.0 <= v <= 1.0:
            raise ValueError("map_confidence must be between 0.0 and 1.0")
        return v


class MappingMetadataSchema(MetadataSchema):
    """Extended metadata for mapping.yaml."""

    source_index: str | None = None
    target_index: str | None = None
    mapped_count: int | None = None
    unmapped_count: int | None = None
    to_audit: int | None = None
    unused_sources: int | None = None
    unused_targets: int | None = None


class MappingSchema(BaseModel):
    """Schema for mapping.yaml."""

    metadata: MappingMetadataSchema
    mappings: list[MappingFieldSchema] | None = None
    skipped: list[dict[str, Any]] | None = None
    unmapped_sources: list[dict[str, Any]] | None = None
    unmapped_targets: list[dict[str, Any]] | None = None


def validate_config(data: dict[str, Any]) -> ConfigSchema:
    """
    Validate config.yaml data.

    Args:
        data: Dictionary containing config data

    Returns:
        Validated ConfigSchema instance

    Raises:
        ValidationError: If validation fails
    """
    try:
        return ConfigSchema(**data)
    except Exception as e:
        raise ValidationError(f"Config validation failed: {e}") from e


def validate_central_mapping_memory(data: dict[str, Any]) -> CentralMappingMemorySchema:
    """
    Validate central_mapping_memory.yaml data.

    Args:
        data: Dictionary containing central mapping memory data

    Returns:
        Validated CentralMappingMemorySchema instance

    Raises:
        ValidationError: If validation fails
    """
    try:
        return CentralMappingMemorySchema(**data)
    except Exception as e:
        raise ValidationError(f"Central mapping memory validation failed: {e}") from e


def validate_index_source(data: dict[str, Any]) -> IndexSourceSchema:
    """
    Validate index_source.yaml data.

    Args:
        data: Dictionary containing index source data

    Returns:
        Validated IndexSourceSchema instance

    Raises:
        ValidationError: If validation fails
    """
    try:
        return IndexSourceSchema(**data)
    except Exception as e:
        raise ValidationError(f"Index source validation failed: {e}") from e


def validate_index_target(data: dict[str, Any]) -> IndexTargetSchema:
    """
    Validate index_target.yaml data.

    Args:
        data: Dictionary containing index target data

    Returns:
        Validated IndexTargetSchema instance

    Raises:
        ValidationError: If validation fails
    """
    try:
        return IndexTargetSchema(**data)
    except Exception as e:
        raise ValidationError(f"Index target validation failed: {e}") from e


def validate_mapping(data: dict[str, Any]) -> MappingSchema:
    """
    Validate mapping.yaml data.

    Args:
        data: Dictionary containing mapping data

    Returns:
        Validated MappingSchema instance

    Raises:
        ValidationError: If validation fails
    """
    try:
        return MappingSchema(**data)
    except Exception as e:
        raise ValidationError(f"Mapping validation failed: {e}") from e
