#!/usr/bin/env python3
"""
Source-based mapping pipeline for transform-myd-minimal.

Implements direct mapping generation from source files:
- Source headers from XLSX files
- Target fields from SpreadsheetML XML files
- Enhanced matching logic for connecting source to target
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from .fuzzy import FieldNormalizer, FuzzyConfig, FuzzyMatcher
from .logging_config import get_logger
from .parsers import parse_source_and_targets
from .synonym import SynonymMatcher

# Initialize logger for this module
logger = get_logger(__name__)


class SourceBasedMatcher:
    """Enhanced field matcher for source-based mapping workflow."""

    def __init__(self, fuzzy_config: Optional[FuzzyConfig] = None):
        self.fuzzy_config = fuzzy_config or FuzzyConfig()
        self.normalizer = FieldNormalizer()
        self.fuzzy_matcher = FuzzyMatcher()
        self.synonym_matcher = SynonymMatcher()

    def match_sources_to_targets(
        self,
        source_headers: List[str],
        target_fields: List[Dict[str, Any]],
        priority_fields: List[str] = None,
    ) -> Dict[str, Any]:
        """
        Match source headers to target fields using enhanced strategies.

        Args:
            source_headers: List of source field names
            target_fields: List of target field dictionaries
            priority_fields: List of target field keys to prioritize for matching

        Returns:
            Dictionary with matching results
        """
        if priority_fields is None:
            priority_fields = ["description", "sap_field", "group_name"]

        matches = []
        unmatched_sources = []

        # Create lookup dictionaries for different target field attributes
        target_lookups = {
            "description": {},
            "sap_field": {},
            "group_name": {},
            "internal_id": {},
            "transformer_id": {},
        }

        for target in target_fields:
            for key in target_lookups:
                if target.get(key):
                    target_lookups[key][target[key].lower()] = target

        # Track which targets have been matched to avoid duplicates
        matched_targets = set()

        for source_header in source_headers:
            best_match = None
            best_confidence = 0.0
            match_type = "no_match"
            match_reason = "No suitable match found"

            # Try exact matches first on prioritized fields
            for priority_field in priority_fields:
                if source_header.lower() in target_lookups[priority_field]:
                    target = target_lookups[priority_field][source_header.lower()]
                    target_key = target["transformer_id"]

                    if target_key not in matched_targets:
                        best_match = target
                        best_confidence = 1.0
                        match_type = "exact"
                        match_reason = f"Exact match on {priority_field}"
                        matched_targets.add(target_key)
                        break

            # If no exact match, try fuzzy matching
            if not best_match and self.fuzzy_config.enabled:
                source_norm = self.normalizer.normalize_field_name(source_header)

                for target in target_fields:
                    target_key = target["transformer_id"]
                    if target_key in matched_targets:
                        continue

                    # Check synonym match first
                    if self.synonym_matcher.is_synonym_match(
                        source_header, target.get("sap_field", "")
                    ):
                        if best_confidence < 0.85:
                            best_match = target
                            best_confidence = 0.85
                            match_type = "synonym"
                            match_reason = "Synonym match found"

                    # Try fuzzy matching on various target fields
                    for priority_field in priority_fields:
                        target_value = target.get(priority_field, "")
                        if not target_value:
                            continue

                        target_norm = self.normalizer.normalize_field_name(target_value)

                        # Calculate fuzzy similarity
                        lev_sim = (
                            self.fuzzy_matcher.levenshtein_similarity(
                                source_norm, target_norm
                            )
                            if self.fuzzy_config.use_levenshtein
                            else 0.0
                        )
                        jw_sim = (
                            self.fuzzy_matcher.jaro_winkler_similarity(
                                source_norm, target_norm
                            )
                            if self.fuzzy_config.use_jaro_winkler
                            else 0.0
                        )

                        combined_sim = (
                            lev_sim * self.fuzzy_config.levenshtein_weight
                            + jw_sim * self.fuzzy_config.jaro_winkler_weight
                        )

                        if (
                            combined_sim >= self.fuzzy_config.threshold
                            and combined_sim > best_confidence
                        ):
                            best_match = target
                            best_confidence = combined_sim
                            match_type = "fuzzy"
                            match_reason = f"Fuzzy match on {priority_field} (similarity: {combined_sim:.2f})"

                # Mark the best fuzzy match as matched
                if best_match:
                    matched_targets.add(best_match["transformer_id"])

            # Record the match result
            if best_match:
                matches.append(
                    {
                        "source": source_header,
                        "internal_id": best_match["internal_id"],
                        "transformer_id": best_match["transformer_id"],
                        "method": match_type,
                        "confidence": best_confidence,
                        "reason": match_reason,
                        "target_info": best_match,
                    }
                )
            else:
                unmatched_sources.append(
                    {"source": source_header, "reason": match_reason}
                )

        # Find unmatched targets
        matched_target_ids = {match["transformer_id"] for match in matches}
        unmatched_targets = [
            target
            for target in target_fields
            if target["transformer_id"] not in matched_target_ids
        ]

        return {
            "matches": matches,
            "unmatched_sources": unmatched_sources,
            "unmatched_targets": unmatched_targets,
            "stats": {
                "total_sources": len(source_headers),
                "total_targets": len(target_fields),
                "matched_sources": len(matches),
                "coverage_percentage": (
                    (len(matches) / len(source_headers) * 100) if source_headers else 0
                ),
            },
        }


def generate_targets_yaml(
    target_fields: List[Dict[str, Any]], output_path: Path
) -> None:
    """
    Generate targets.yaml with target field metadata.

    Args:
        target_fields: List of target field dictionaries
        output_path: Path to write the targets.yaml file
    """
    from datetime import datetime

    import yaml

    targets_data = {
        "metadata": {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_fields": len(target_fields),
            "generator": "transform-myd-minimal source-based mapping",
        },
        "targets": [],
    }

    for target in target_fields:
        target_entry = {
            "sap_field": target["sap_field"],  # sap_field first for readability
            "internal_id": target["internal_id"],
            "transformer_id": target["transformer_id"],
            "sap_table": target["sap_table"],
            "description": target.get("description", ""),
            "group": target.get("group_name", ""),
            "importance": target.get("importance", ""),
            "type": target.get("type", ""),
            "length": target.get("length", ""),
        }
        # Only add decimal if it's not null/empty to avoid "decimal: null"
        decimal_value = target.get("decimal", "")
        if decimal_value:
            target_entry["decimal"] = decimal_value

        targets_data["targets"].append(target_entry)

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write YAML file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# Target fields metadata generated by transform-myd-minimal\n")
        f.write(f"# Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        yaml.dump(targets_data, f, default_flow_style=False, allow_unicode=True)

    logger.info(f"Generated targets.yaml: {output_path}")


def generate_mapping_yaml(mapping_result: Dict[str, Any], output_path: Path) -> None:
    """
    Generate mapping.yaml with source-to-target mapping results.

    Args:
        mapping_result: Result from source-based matching
        output_path: Path to write the mapping.yaml file
    """
    from datetime import datetime

    import yaml

    mapping_data = {
        "metadata": {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "generator": "transform-myd-minimal source-based mapping",
            "stats": mapping_result["stats"],
        },
        "mappings": [],
        "unmatched_sources": [],
        "unmatched_targets": [],
    }

    # Add successful mappings
    for match in mapping_result["matches"]:
        mapping_entry = {
            "source": match["source"],
            "internal_id": match["internal_id"],
            "transformer_id": match["transformer_id"],
            "method": match["method"],
            "confidence": round(match["confidence"], 3),
            "description": match["target_info"].get("description", ""),
            "sap_table": match["target_info"]["sap_table"],
            "sap_field": match["target_info"]["sap_field"],
        }
        mapping_data["mappings"].append(mapping_entry)

    # Add unmatched sources
    for unmatched in mapping_result["unmatched_sources"]:
        mapping_data["unmatched_sources"].append(
            {"source": unmatched["source"], "reason": unmatched["reason"]}
        )

    # Add unmatched targets
    for target in mapping_result["unmatched_targets"]:
        mapping_data["unmatched_targets"].append(
            {
                "internal_id": target["internal_id"],
                "transformer_id": target["transformer_id"],
                "description": target.get("description", ""),
                "sap_table": target["sap_table"],
                "sap_field": target["sap_field"],
            }
        )

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write YAML file with custom formatting for better readability
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(
            "# Source-to-target field mappings generated by transform-myd-minimal\n"
        )
        f.write(f"# Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(
            f"# Coverage: {mapping_result['stats']['coverage_percentage']:.1f}%\n\n"
        )

        # Write metadata section
        metadata_data = {"metadata": mapping_data["metadata"]}
        yaml.dump(metadata_data, f, default_flow_style=False, allow_unicode=True)
        f.write("\n")  # Add empty line after metadata

        # Write mappings section
        mappings_section = {"mappings": mapping_data["mappings"]}
        yaml.dump(mappings_section, f, default_flow_style=False, allow_unicode=True)
        f.write("\n")  # Add empty line after mappings

        # Write unmatched sources section
        if mapping_data["unmatched_sources"]:
            unmatched_sources_section = {
                "unmatched_sources": mapping_data["unmatched_sources"]
            }
            yaml.dump(
                unmatched_sources_section,
                f,
                default_flow_style=False,
                allow_unicode=True,
            )
            f.write("\n")  # Add empty line after unmatched_sources

        # Write unmatched targets section
        if mapping_data["unmatched_targets"]:
            unmatched_targets_section = {
                "unmatched_targets": mapping_data["unmatched_targets"]
            }
            yaml.dump(
                unmatched_targets_section,
                f,
                default_flow_style=False,
                allow_unicode=True,
            )

    logger.info(f"Generated mapping.yaml: {output_path}")


def run_source_based_mapping(config, args=None) -> None:
    """
    Run the complete source-based mapping pipeline.

    Args:
        config: Configuration object
        args: CLI arguments (optional)
    """
    logger.info("=== Source-Based Mapping Pipeline ===")

    # Determine file paths
    source_path = Path(config.source_headers["path"])
    target_path = Path(config.target_xml["path"])

    logger.info(f"Source headers file: {source_path}")
    logger.info(f"Target XML file: {target_path}")

    # Parse source headers and target fields
    logger.info("\nParsing source and target files...")
    try:
        source_headers, target_fields = parse_source_and_targets(
            source_path,
            target_path,
            source_config=config.source_headers,
            target_config={
                "worksheet_name": config.target_xml["worksheet_name"],
                "header_match": config.target_xml["header_match"],
            },
        )

        logger.info(f"✓ Found {len(source_headers)} source headers")
        logger.info(f"✓ Found {len(target_fields)} target fields")

    except Exception as e:
        logger.info(f"Error parsing files: {e}")
        return

    # Run matching
    logger.info("\nRunning field matching...")
    fuzzy_config = FuzzyConfig(
        enabled=not config.disable_fuzzy,
        threshold=config.fuzzy_threshold,
        max_suggestions=config.max_suggestions,
    )

    matcher = SourceBasedMatcher(fuzzy_config)
    mapping_result = matcher.match_sources_to_targets(
        source_headers, target_fields, config.matching["target_label_priority"]
    )

    # Print results
    logger.info("\n=== Matching Results ===")
    logger.info(f"Total source fields: {mapping_result['stats']['total_sources']}")
    logger.info(f"Total target fields: {mapping_result['stats']['total_targets']}")
    logger.info(f"Successful matches: {mapping_result['stats']['matched_sources']}")
    logger.info(f"Coverage: {mapping_result['stats']['coverage_percentage']:.1f}%")
    logger.info(f"Unmatched sources: {len(mapping_result['unmatched_sources'])}")
    logger.info(f"Unmatched targets: {len(mapping_result['unmatched_targets'])}")

    # Generate output files
    output_dir = Path(config.output_dir)

    logger.info("\n=== Generating Output Files ===")
    generate_targets_yaml(target_fields, output_dir / "targets.yaml")
    generate_mapping_yaml(mapping_result, output_dir / "mapping.yaml")

    logger.info("\n✓ Source-based mapping pipeline completed successfully!")
