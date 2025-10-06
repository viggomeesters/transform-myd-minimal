#!/usr/bin/env python3
"""
Test transform.yaml generation functionality for F04.
"""
from pathlib import Path

import yaml


class MockArgs:
    """Mock arguments for testing."""

    def __init__(
        self, object_name="test_obj", variant="test_var", root=None, force=True
    ):
        self.object = object_name
        self.variant = variant
        self.root = root
        self.force = force
        self.prefer_xlsx = False
        self.json = False
        self.format = "human"
        self.log_file = None
        self.no_log_file = True
        self.no_preview = True
        self.quiet = True
        self.no_html = True
        self.html_dir = None


def test_transform_yaml_generation():
    """Test that transform.yaml is generated alongside validation.yaml."""
    # Test with the actual existing structure - use Path.cwd() for cross-platform compatibility
    repo_root = Path.cwd()
    migrations_dir = repo_root / "migrations" / "m140" / "bnka"

    # Check that transform.yaml was created in our earlier test
    transform_file = migrations_dir / "transform.yaml"
    assert transform_file.exists(), "transform.yaml should be generated"

    # Check that validation.yaml was also created
    validation_file = migrations_dir / "validation.yaml"
    assert validation_file.exists(), "validation.yaml should be generated"

    # Parse and validate transform.yaml structure
    with open(transform_file, encoding="utf-8") as f:
        transform_data = yaml.safe_load(f)

    # Check required structure
    assert "metadata" in transform_data
    assert "transformations" in transform_data
    assert "transformation_settings" in transform_data

    # Check metadata
    metadata = transform_data["metadata"]
    assert metadata["object"] == "m140"
    assert metadata["variant"] == "bnka"
    assert "generated_at" in metadata
    assert "description" in metadata

    # Check transformations structure
    transformations = transform_data["transformations"]
    assert len(transformations) > 0, "Should have transformation rules"

    # Check first transformation has required fields
    first_transform = transformations[0]
    assert "target_field" in first_transform
    assert "target_field_description" in first_transform
    assert "transformation_type" in first_transform
    assert "placeholder_value" in first_transform
    assert "value_mappings" in first_transform

    # Check transformation settings
    settings = transform_data["transformation_settings"]
    assert "null_handling" in settings
    assert "empty_string_handling" in settings
    assert "case_sensitive_mappings" in settings
    assert "trim_whitespace" in settings

    print(
        f"✓ transform.yaml generated successfully with {len(transformations)} transformation rules"
    )


def test_transform_yaml_structure_requirements():
    """Test that transform.yaml meets all the requirements from the problem statement."""
    # Test with the actual existing structure - use Path.cwd() for cross-platform compatibility
    repo_root = Path.cwd()
    migrations_dir = repo_root / "migrations" / "m140" / "bnka"

    # Check that transform.yaml was created
    transform_file = migrations_dir / "transform.yaml"
    assert transform_file.exists(), "transform.yaml should be generated"

    # Parse and validate transform.yaml structure
    with open(transform_file, encoding="utf-8") as f:
        transform_data = yaml.safe_load(f)

    # Requirement 1: List of target fields
    transformations = transform_data["transformations"]
    assert len(transformations) > 0, "Should have a list of target fields"

    # Requirement 2: Ability to map a value to another value
    for transform in transformations:
        assert "value_mappings" in transform, "Each field should support value mappings"

    # Requirement 3: Ability to add a placeholder value
    for transform in transformations:
        assert (
            "placeholder_value" in transform
        ), "Each field should support placeholder values"

    # Additional checks for usability
    for transform in transformations:
        assert transform["target_field"], "Target field should not be empty"
        assert "transformation_type" in transform, "Should have transformation type"
        assert (
            "target_field_description" in transform
        ), "Should have target field description"

    print(
        "✓ All requirements met: target fields list, value mappings, and placeholder values"
    )


if __name__ == "__main__":
    # Allow running this test directly
    test_transform_yaml_generation()
    test_transform_yaml_structure_requirements()
    print("All transform.yaml tests passed!")
