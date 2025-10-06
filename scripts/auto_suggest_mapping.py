#!/usr/bin/env python3
"""
Auto-suggest mapping script for transform-myd-minimal.

Provides automatic mapping suggestions based on:
- Field name similarity (fuzzy matching)
- Data type matching
- Sample value analysis
"""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import yaml

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from transform_myd_minimal.fuzzy import FieldNormalizer, FuzzyMatcher


class AutoSuggestMapper:
    """Automatic mapping suggestion engine."""

    def __init__(
        self,
        fuzzy_threshold: float = 0.6,
        max_suggestions: int = 3,
    ):
        """Initialize the auto-suggest mapper.

        Args:
            fuzzy_threshold: Minimum similarity score for fuzzy matches (0.0-1.0)
            max_suggestions: Maximum number of suggestions to return per field
        """
        self.fuzzy_threshold = fuzzy_threshold
        self.max_suggestions = max_suggestions
        self.normalizer = FieldNormalizer()
        self.fuzzy_matcher = FuzzyMatcher()

    def suggest_mappings(
        self,
        source_fields: List[Dict[str, Any]],
        target_fields: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Generate mapping suggestions for source fields.

        Args:
            source_fields: List of source field dictionaries with 'name', 'dtype', 'samples'
            target_fields: List of target field dictionaries with 'name', 'dtype', 'description'

        Returns:
            List of mapping suggestions with confidence scores
        """
        suggestions = []

        for source in source_fields:
            source_name = source.get("name", "")
            source_dtype = source.get("dtype", "")
            source_samples = source.get("samples", [])

            # Find best matches
            matches = self._find_matches(
                source_name,
                source_dtype,
                source_samples,
                target_fields,
            )

            if matches:
                suggestions.append(
                    {
                        "source_field": source_name,
                        "source_dtype": source_dtype,
                        "suggestions": matches[: self.max_suggestions],
                    }
                )

        return suggestions

    def _find_matches(
        self,
        source_name: str,
        source_dtype: str,
        source_samples: List[Any],
        target_fields: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Find matching target fields for a source field.

        Args:
            source_name: Name of the source field
            source_dtype: Data type of the source field
            source_samples: Sample values from the source field
            target_fields: List of target field dictionaries

        Returns:
            List of matches sorted by confidence score (highest first)
        """
        matches = []
        source_norm = self.normalizer.normalize_field_name(source_name)

        for target in target_fields:
            target_name = target.get("name", "")
            target_dtype = target.get("dtype", "")
            target_desc = target.get("description", "")

            # Calculate name similarity
            target_norm = self.normalizer.normalize_field_name(target_name)
            lev_sim = self.fuzzy_matcher.levenshtein_similarity(source_norm, target_norm)
            jw_sim = self.fuzzy_matcher.jaro_winkler_similarity(source_norm, target_norm)
            name_similarity = (lev_sim + jw_sim) / 2  # Average of both algorithms

            # Calculate description similarity if available
            desc_similarity = 0.0
            if target_desc:
                source_desc_norm = self.normalizer.normalize_description(source_name)
                target_desc_norm = self.normalizer.normalize_description(target_desc)
                lev_desc = self.fuzzy_matcher.levenshtein_similarity(
                    source_desc_norm, target_desc_norm
                )
                jw_desc = self.fuzzy_matcher.jaro_winkler_similarity(
                    source_desc_norm, target_desc_norm
                )
                desc_similarity = (lev_desc + jw_desc) / 2

            # Calculate dtype match score
            dtype_score = 1.0 if self._dtype_compatible(source_dtype, target_dtype) else 0.5

            # Calculate sample value match score
            sample_score = self._calculate_sample_score(source_samples, target)

            # Combined confidence score
            # Weights: name (40%), description (20%), dtype (20%), samples (20%)
            confidence = (
                name_similarity * 0.4
                + desc_similarity * 0.2
                + dtype_score * 0.2
                + sample_score * 0.2
            )

            if confidence >= self.fuzzy_threshold:
                matches.append(
                    {
                        "target_field": target_name,
                        "target_dtype": target_dtype,
                        "confidence": round(confidence, 3),
                        "name_similarity": round(name_similarity, 3),
                        "dtype_match": dtype_score == 1.0,
                        "reason": self._generate_reason(
                            name_similarity,
                            desc_similarity,
                            dtype_score,
                            sample_score,
                        ),
                    }
                )

        # Sort by confidence (highest first)
        matches.sort(key=lambda x: x["confidence"], reverse=True)
        return matches

    def _dtype_compatible(self, source_dtype: str, target_dtype: str) -> bool:
        """Check if source and target data types are compatible.

        Args:
            source_dtype: Source field data type
            target_dtype: Target field data type

        Returns:
            True if types are compatible, False otherwise
        """
        # Normalize dtype strings
        source_dtype = str(source_dtype).lower()
        target_dtype = str(target_dtype).lower()

        # Define compatible type groups
        string_types = {"object", "string", "str", "varchar", "char", "text"}
        numeric_types = {"int", "int64", "int32", "float", "float64", "number", "numeric", "decimal"}
        date_types = {"datetime", "datetime64", "date", "timestamp"}
        bool_types = {"bool", "boolean"}

        # Check if both types are in the same group
        for type_group in [string_types, numeric_types, date_types, bool_types]:
            if source_dtype in type_group and target_dtype in type_group:
                return True

        return False

    def _calculate_sample_score(
        self,
        source_samples: List[Any],
        target: Dict[str, Any],
    ) -> float:
        """Calculate a score based on sample value analysis.

        Args:
            source_samples: List of sample values from source field
            target: Target field dictionary

        Returns:
            Sample match score (0.0-1.0)
        """
        if not source_samples:
            return 0.5  # Neutral score if no samples

        # Check for patterns in field name that might indicate content
        target_name = target.get("name", "").lower()
        target_desc = target.get("description", "").lower()

        # Analyze sample values
        sample_str = " ".join(str(s) for s in source_samples if s is not None).lower()

        # Look for keywords in target field that match sample patterns
        score = 0.5  # Start with neutral
        
        # If target name/desc contains keywords that appear in samples, boost score
        keywords = ["bank", "account", "name", "code", "id", "date", "amount", "currency"]
        for keyword in keywords:
            if keyword in target_name or keyword in target_desc:
                if keyword in sample_str:
                    score = min(1.0, score + 0.2)

        return score

    def _generate_reason(
        self,
        name_sim: float,
        desc_sim: float,
        dtype_score: float,
        sample_score: float,
    ) -> str:
        """Generate a human-readable reason for the match.

        Args:
            name_sim: Name similarity score
            desc_sim: Description similarity score
            dtype_score: Data type match score
            sample_score: Sample value match score

        Returns:
            Reason string
        """
        reasons = []

        if name_sim >= 0.8:
            reasons.append(f"High name similarity ({name_sim:.1%})")
        elif name_sim >= 0.6:
            reasons.append(f"Moderate name similarity ({name_sim:.1%})")

        if desc_sim >= 0.6:
            reasons.append(f"Description match ({desc_sim:.1%})")

        if dtype_score == 1.0:
            reasons.append("Compatible data types")

        if sample_score > 0.6:
            reasons.append("Sample value patterns match")

        return "; ".join(reasons) if reasons else "General similarity"


def load_source_fields_from_yaml(yaml_path: Path) -> List[Dict[str, Any]]:
    """Load source fields from YAML index file.

    Args:
        yaml_path: Path to index_source.yaml file

    Returns:
        List of source field dictionaries
    """
    with open(yaml_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    source_fields = []
    for field in data.get("source_fields", []):
        # Try different field name keys for compatibility
        field_name = (
            field.get("field_name")
            or field.get("source_field_name")
            or field.get("name")
            or ""
        )
        field_type = (
            field.get("field_type")
            or field.get("source_dtype")
            or field.get("dtype")
            or ""
        )
        examples = (
            field.get("example_values")
            or field.get("source_example")
            or field.get("examples")
            or []
        )
        
        # Ensure examples is a list
        if not isinstance(examples, list):
            examples = [examples] if examples else []

        source_fields.append(
            {
                "name": field_name,
                "dtype": field_type,
                "samples": examples,
            }
        )

    return source_fields


def load_target_fields_from_yaml(yaml_path: Path) -> List[Dict[str, Any]]:
    """Load target fields from YAML index file.

    Args:
        yaml_path: Path to index_target.yaml file

    Returns:
        List of target field dictionaries
    """
    with open(yaml_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    target_fields = []
    for field in data.get("target_fields", []):
        # Try different field name keys for compatibility
        field_name = (
            field.get("sap_field")
            or field.get("target_field_name")
            or field.get("name")
            or ""
        )
        field_type = (
            field.get("data_type")
            or field.get("target_data_type")
            or field.get("dtype")
            or ""
        )
        description = (
            field.get("description")
            or field.get("target_field_description")
            or field.get("desc")
            or ""
        )

        target_fields.append(
            {
                "name": field_name,
                "dtype": field_type,
                "description": description,
            }
        )

    return target_fields


def main():
    """Main entry point for auto-suggest mapping."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Auto-suggest field mappings based on fuzzy matching and data analysis"
    )
    parser.add_argument(
        "--object",
        required=True,
        help="Object name (e.g., m140)",
    )
    parser.add_argument(
        "--variant",
        required=True,
        help="Variant name (e.g., bnka)",
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Root directory of the project",
    )
    parser.add_argument(
        "--fuzzy-threshold",
        type=float,
        default=0.6,
        help="Minimum similarity score for suggestions (0.0-1.0)",
    )
    parser.add_argument(
        "--max-suggestions",
        type=int,
        default=3,
        help="Maximum number of suggestions per field",
    )
    parser.add_argument(
        "--output",
        help="Output file for suggestions (default: print to console)",
    )

    args = parser.parse_args()

    # Set up paths
    root_path = Path(args.root)
    migrations_dir = root_path / "migrations" / args.object / args.variant
    source_index = migrations_dir / "index_source.yaml"
    target_index = migrations_dir / "index_target.yaml"

    # Check if files exist
    if not source_index.exists():
        print(f"Error: Source index not found: {source_index}", file=sys.stderr)
        sys.exit(1)

    if not target_index.exists():
        print(f"Error: Target index not found: {target_index}", file=sys.stderr)
        sys.exit(1)

    # Load fields
    print(f"Loading source fields from {source_index}...")
    source_fields = load_source_fields_from_yaml(source_index)
    print(f"Loaded {len(source_fields)} source fields")

    print(f"Loading target fields from {target_index}...")
    target_fields = load_target_fields_from_yaml(target_index)
    print(f"Loaded {len(target_fields)} target fields")

    # Generate suggestions
    print(f"\nGenerating mapping suggestions...")
    mapper = AutoSuggestMapper(
        fuzzy_threshold=args.fuzzy_threshold,
        max_suggestions=args.max_suggestions,
    )
    suggestions = mapper.suggest_mappings(source_fields, target_fields)

    # Output results
    if args.output:
        output_path = Path(args.output)
        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump(
                {"suggestions": suggestions},
                f,
                default_flow_style=False,
                allow_unicode=True,
            )
        print(f"\nSuggestions written to: {output_path}")
    else:
        print(f"\n=== Mapping Suggestions ({len(suggestions)} fields) ===\n")
        for suggestion in suggestions:
            print(f"Source: {suggestion['source_field']} ({suggestion['source_dtype']})")
            for i, match in enumerate(suggestion["suggestions"], 1):
                print(f"  {i}. {match['target_field']} - Confidence: {match['confidence']:.1%}")
                print(f"     Reason: {match['reason']}")
            print()


if __name__ == "__main__":
    main()
