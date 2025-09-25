#!/usr/bin/env python3
"""
Main orchestration and entry point for transform-myd-minimal.

Contains the entrypoint and orchestration of the different modules including:
- Field matching orchestration
- Central mapping memory handling
- Command execution logic
- Core data classes and structures
"""

import sys
import json
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

import pandas as pd
import yaml
from pandas.api.types import infer_dtype
from rich.console import Console
from rich.table import Table

from .cli import setup_cli
from .fuzzy import FuzzyConfig, FieldNormalizer, FuzzyMatcher
from .logging_config import get_logger
from .synonym import SynonymMatcher

# Initialize logger for this module
logger = get_logger(__name__)


# Configure YAML to maintain dictionary order
def represent_ordereddict(dumper, data):
    return dumper.represent_mapping("tag:yaml.org,2002:map", data.items())


yaml.add_representer(OrderedDict, represent_ordereddict)


@dataclass
class FieldMatchResult:
    """Result of a field matching operation."""

    source_field: str
    target_field: Optional[str]
    confidence_score: float
    match_type: str  # "exact", "synoniem", "fuzzy", "geen match"
    reason: str
    source_description: Optional[str] = None
    target_description: Optional[str] = None
    algorithm: Optional[str] = None  # "levenshtein", "jaro_winkler" for fuzzy matches


@dataclass
class SkipRule:
    """Represents a skip rule from central mapping memory."""

    source_field: str
    source_description: str
    skip: bool
    comment: str


@dataclass
class ManualMapping:
    """Represents a manual mapping rule from central mapping memory."""

    source_field: str
    source_description: str
    target: str
    target_description: str
    comment: str


@dataclass
class CentralMappingMemory:
    """Central mapping memory configuration."""

    global_skip_fields: List[SkipRule]
    global_manual_mappings: List[ManualMapping]
    table_specific: Dict[str, Dict[str, List]]
    synonyms: Dict[str, List[str]]


class AdvancedFieldMatcher:
    """Advanced field matching system with multiple strategies."""

    def __init__(self, fuzzy_config: Optional[FuzzyConfig] = None):
        self.fuzzy_config = fuzzy_config or FuzzyConfig()
        self.normalizer = FieldNormalizer()
        self.fuzzy_matcher = FuzzyMatcher()
        self.synonym_matcher = SynonymMatcher()

    def match_fields(
        self, source_fields: pd.DataFrame, target_fields: pd.DataFrame
    ) -> Tuple[List[FieldMatchResult], List[FieldMatchResult]]:
        """
        Match source fields to target fields using comprehensive strategies.

        Returns tuple of (matches, audit_matches) where:
        - matches: List of actual field mappings (exact and non-conflicting fuzzy)
        - audit_matches: List of fuzzy matches to already exact-mapped targets (for audit)
        """
        # Create normalized target lookup
        target_lookup = {}
        for _, target_row in target_fields.iterrows():
            target_name = target_row["field_name"]
            target_desc = target_row["field_description"]
            target_lookup[target_name] = {
                "description": target_desc,
                "normalized_name": self.normalizer.normalize_field_name(target_name),
                "normalized_desc": self.normalizer.normalize_description(target_desc),
                "is_key": target_row.get("field_is_key", False),
                "is_mandatory": target_row.get("field_is_mandatory", False),
            }

        # First pass: Find all exact matches
        exact_mapped_targets = set()
        results = []

        for _, source_row in source_fields.iterrows():
            source_name = source_row["field_name"]
            source_desc = source_row["field_description"]

            exact_match = self._find_exact_match(
                source_name, source_desc, target_lookup
            )
            if exact_match:
                results.append(exact_match)
                exact_mapped_targets.add(exact_match.target_field)

        # Second pass: Find fuzzy/synonym matches excluding already exact-mapped targets
        audit_matches = []

        for _, source_row in source_fields.iterrows():
            source_name = source_row["field_name"]
            source_desc = source_row["field_description"]

            # Skip if we already found an exact match for this source
            if any(r.source_field == source_name for r in results):
                continue

            # Find best non-exact match
            fuzzy_match = self._find_fuzzy_match(
                source_name, source_desc, target_lookup, exact_mapped_targets
            )
            if fuzzy_match:
                results.append(fuzzy_match)
            else:
                # No match found
                results.append(
                    FieldMatchResult(
                        source_field=source_name,
                        target_field=None,
                        confidence_score=0.0,
                        match_type="geen match",
                        reason="Geen geschikte match gevonden",
                        source_description=source_desc,
                    )
                )

            # Check for audit matches (fuzzy matches to exact-mapped targets)
            audit_match = self._find_audit_match(
                source_name, source_desc, target_lookup, exact_mapped_targets
            )
            if audit_match:
                audit_matches.append(audit_match)

        return results, audit_matches

    def _find_exact_match(
        self, source_name: str, source_desc: str, target_lookup: Dict
    ) -> Optional[FieldMatchResult]:
        """Find exact match for a source field."""
        source_norm_name = self.normalizer.normalize_field_name(source_name)
        source_norm_desc = self.normalizer.normalize_description(source_desc)

        # Strategy 1: Exact match on normalized field names
        for target_name, target_info in target_lookup.items():
            if source_norm_name == target_info["normalized_name"]:
                # Additional check: if descriptions are available, they should also match or be similar
                if source_norm_desc and target_info["normalized_desc"]:
                    if source_norm_desc == target_info["normalized_desc"]:
                        confidence = 1.0  # Perfect match
                    else:
                        confidence = 0.95  # Name matches, description differs slightly
                else:
                    confidence = 0.95  # Name matches, no description to verify

                return FieldMatchResult(
                    source_field=source_name,
                    target_field=target_name,
                    confidence_score=confidence,
                    match_type="exact",
                    reason="Exacte match op genormaliseerde veldnaam",
                    source_description=source_desc,
                    target_description=target_info["description"],
                )
        return None

    def _find_fuzzy_match(
        self,
        source_name: str,
        source_desc: str,
        target_lookup: Dict,
        exact_mapped_targets: set,
    ) -> Optional[FieldMatchResult]:
        """Find fuzzy/synonym match for a source field, excluding exact-mapped targets."""
        if not self.fuzzy_config.enabled:
            return None

        source_norm_name = self.normalizer.normalize_field_name(source_name)
        source_norm_desc = self.normalizer.normalize_description(source_desc)

        best_match = None
        best_score = 0.0

        for target_name, target_info in target_lookup.items():
            # Skip if this target is already exact-mapped
            if target_name in exact_mapped_targets:
                continue

            # Check for synonym match first
            if self.synonym_matcher.is_synonym_match(source_name, target_name):
                return FieldMatchResult(
                    source_field=source_name,
                    target_field=target_name,
                    confidence_score=0.85,
                    match_type="synoniem",
                    reason="Synoniem match gevonden",
                    source_description=source_desc,
                    target_description=target_info["description"],
                )

            # Fuzzy matching
            if self.fuzzy_config.use_levenshtein or self.fuzzy_config.use_jaro_winkler:
                # Calculate name similarity
                name_sim_lev = (
                    self.fuzzy_matcher.levenshtein_similarity(
                        source_norm_name, target_info["normalized_name"]
                    )
                    if self.fuzzy_config.use_levenshtein
                    else 0.0
                )

                name_sim_jw = (
                    self.fuzzy_matcher.jaro_winkler_similarity(
                        source_norm_name, target_info["normalized_name"]
                    )
                    if self.fuzzy_config.use_jaro_winkler
                    else 0.0
                )

                # Combined name similarity
                name_similarity = (
                    name_sim_lev * self.fuzzy_config.levenshtein_weight
                    + name_sim_jw * self.fuzzy_config.jaro_winkler_weight
                )

                # Description similarity (if available)
                desc_similarity = 0.0
                if source_norm_desc and target_info["normalized_desc"]:
                    desc_sim_lev = (
                        self.fuzzy_matcher.levenshtein_similarity(
                            source_norm_desc, target_info["normalized_desc"]
                        )
                        if self.fuzzy_config.use_levenshtein
                        else 0.0
                    )

                    desc_sim_jw = (
                        self.fuzzy_matcher.jaro_winkler_similarity(
                            source_norm_desc, target_info["normalized_desc"]
                        )
                        if self.fuzzy_config.use_jaro_winkler
                        else 0.0
                    )

                    desc_similarity = (
                        desc_sim_lev * self.fuzzy_config.levenshtein_weight
                        + desc_sim_jw * self.fuzzy_config.jaro_winkler_weight
                    )

                # Combined score: 70% name, 30% description
                if source_norm_desc and target_info["normalized_desc"]:
                    combined_score = 0.7 * name_similarity + 0.3 * desc_similarity
                else:
                    combined_score = name_similarity

                if (
                    combined_score >= self.fuzzy_config.threshold
                    and combined_score > best_score
                ):
                    best_score = combined_score
                    algorithm = (
                        "levenshtein"
                        if self.fuzzy_config.levenshtein_weight
                        > self.fuzzy_config.jaro_winkler_weight
                        else "jaro_winkler"
                    )
                    best_match = FieldMatchResult(
                        source_field=source_name,
                        target_field=target_name,
                        confidence_score=combined_score,
                        match_type="fuzzy",
                        reason=f"Fuzzy match (similarity: {combined_score:.2f})",
                        source_description=source_desc,
                        target_description=target_info["description"],
                        algorithm=algorithm,
                    )

        return best_match

    def _find_audit_match(
        self,
        source_name: str,
        source_desc: str,
        target_lookup: Dict,
        exact_mapped_targets: set,
    ) -> Optional[FieldMatchResult]:
        """Find fuzzy matches to exact-mapped targets for audit purposes."""
        if not self.fuzzy_config.enabled or not exact_mapped_targets:
            return None

        source_norm_name = self.normalizer.normalize_field_name(source_name)

        best_match = None
        best_score = 0.0

        # Only check exact-mapped targets
        for target_name in exact_mapped_targets:
            target_info = target_lookup[target_name]

            # Calculate similarity to this exact-mapped target
            name_sim_lev = (
                self.fuzzy_matcher.levenshtein_similarity(
                    source_norm_name, target_info["normalized_name"]
                )
                if self.fuzzy_config.use_levenshtein
                else 0.0
            )

            name_sim_jw = (
                self.fuzzy_matcher.jaro_winkler_similarity(
                    source_norm_name, target_info["normalized_name"]
                )
                if self.fuzzy_config.use_jaro_winkler
                else 0.0
            )

            name_similarity = (
                name_sim_lev * self.fuzzy_config.levenshtein_weight
                + name_sim_jw * self.fuzzy_config.jaro_winkler_weight
            )

            if (
                name_similarity >= self.fuzzy_config.threshold
                and name_similarity > best_score
            ):
                best_score = name_similarity
                algorithm = (
                    "levenshtein"
                    if self.fuzzy_config.levenshtein_weight
                    > self.fuzzy_config.jaro_winkler_weight
                    else "jaro_winkler"
                )
                best_match = FieldMatchResult(
                    source_field=source_name,
                    target_field=target_name,
                    confidence_score=name_similarity,
                    match_type="audit",
                    reason=f"Fuzzy match to exact-mapped target (audit, similarity: {name_similarity:.2f})",
                    source_description=source_desc,
                    target_description=target_info["description"],
                    algorithm=algorithm,
                )

        return best_match


def create_advanced_column_mapping(
    source_fields,
    target_fields,
    fuzzy_config=None,
    central_memory=None,
    object_name=None,
    variant=None,
):
    """Create advanced column mapping using comprehensive matching strategies with central mapping memory support."""

    # Initialize the advanced matcher
    matcher = AdvancedFieldMatcher(fuzzy_config)

    # Initialize tracking for central memory rules
    central_skip_matches = []
    central_manual_matches = []

    # Get effective rules from central mapping memory
    skip_rules, manual_mappings = get_effective_rules_for_table(
        central_memory, object_name or "", variant or ""
    )

    # Apply skip rules first - remove skipped source fields
    filtered_source_fields = source_fields.copy()
    if skip_rules:
        skip_dict = {rule.source_field: rule for rule in skip_rules if rule.skip}

        for source_field in skip_dict:
            # Find matching rows in source_fields and mark for removal
            mask = filtered_source_fields["field_name"] == source_field
            if mask.any():
                # Create skip match result for logging
                row = filtered_source_fields[mask].iloc[0]
                rule = skip_dict[source_field]
                skip_result = FieldMatchResult(
                    source_field=source_field,
                    target_field=None,  # Skipped fields have no target
                    confidence_score=1.0,
                    match_type="central_skip",
                    reason=f"Central memory skip rule: {rule.comment}",
                    source_description=row.get("field_description", ""),
                    target_description=None,
                    algorithm="central_memory",
                )
                central_skip_matches.append(skip_result)

                # Remove from source fields for further processing
                filtered_source_fields = filtered_source_fields[~mask]

    # Apply manual mappings next
    remaining_source_fields = filtered_source_fields.copy()
    if manual_mappings:
        mapping_dict = {mapping.source_field: mapping for mapping in manual_mappings}

        for source_field, mapping in mapping_dict.items():
            # Find matching rows in remaining source fields
            mask = remaining_source_fields["field_name"] == source_field
            if mask.any():
                # Create manual mapping result for logging
                row = remaining_source_fields[mask].iloc[0]
                manual_result = FieldMatchResult(
                    source_field=source_field,
                    target_field=mapping.target,
                    confidence_score=1.0,
                    match_type="central_manual",
                    reason=f"Central memory manual mapping: {mapping.comment}",
                    source_description=row.get("field_description", ""),
                    target_description=mapping.target_description,
                    algorithm="central_memory",
                )
                central_manual_matches.append(manual_result)

                # Remove from source fields for further processing
                remaining_source_fields = remaining_source_fields[~mask]

    # Run advanced matching on remaining fields
    matches, audit_matches = matcher.match_fields(
        remaining_source_fields, target_fields
    )

    # Combine all matches for final result
    all_matches = central_manual_matches + matches

    # Create mapping lines for YAML generation
    mapping_lines = []
    exact_matches = []
    fuzzy_matches = []
    unmapped_sources = []

    for match in all_matches:
        if match.target_field:
            if match.match_type in ["exact", "central_manual"]:
                exact_matches.append(match)
            else:
                fuzzy_matches.append(match)
            mapping_lines.append(f"{match.source_field}: {match.target_field}")
        else:
            unmapped_sources.append(match)
            mapping_lines.append(f"# {match.source_field}: # {match.reason}")

    return (
        mapping_lines,
        exact_matches,
        fuzzy_matches,
        unmapped_sources,
        audit_matches,
        central_skip_matches,
        central_manual_matches,
    )


def create_column_mapping(source_fields, target_fields):
    """Legacy column mapping function - maintained for backward compatibility."""
    result = create_advanced_column_mapping(source_fields, target_fields)
    # Handle both old and new return formats
    if len(result) == 7:
        mapping_lines, _, _, _, _, _, _ = result
    else:
        mapping_lines, _, _, _, _ = result
    return mapping_lines


def load_central_mapping_memory(base_path: Path) -> Optional[CentralMappingMemory]:
    """Load central mapping memory from YAML file."""
    # Look in config directory first, fallback to root for backward compatibility
    central_memory_path = base_path / "config" / "central_mapping_memory.yaml"
    if not central_memory_path.exists():
        central_memory_path = base_path / "central_mapping_memory.yaml"

    if not central_memory_path.exists():
        return None

    try:
        with open(central_memory_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not data:
            return None

        # Parse global skip fields
        global_skip_fields = []
        for skip_data in data.get("global_skip_fields", []):
            global_skip_fields.append(
                SkipRule(
                    source_field=skip_data["source_field"],
                    source_description=skip_data["source_description"],
                    skip=skip_data["skip"],
                    comment=skip_data["comment"],
                )
            )

        # Parse global manual mappings
        global_manual_mappings = []
        for mapping_data in data.get("global_manual_mappings", []):
            global_manual_mappings.append(
                ManualMapping(
                    source_field=mapping_data["source_field"],
                    source_description=mapping_data["source_description"],
                    target=mapping_data["target"],
                    target_description=mapping_data["target_description"],
                    comment=mapping_data["comment"],
                )
            )

        # Parse table-specific rules (keep as dict for flexible processing)
        table_specific = data.get("table_specific", {})
        
        # Parse synonyms
        synonyms = data.get("synonyms", {})

        return CentralMappingMemory(
            global_skip_fields=global_skip_fields,
            global_manual_mappings=global_manual_mappings,
            table_specific=table_specific,
            synonyms=synonyms,
        )

    except Exception as e:
        logger.warning(f"Could not load central mapping memory: {e}")
        return None


def get_effective_rules_for_table(
    central_memory: CentralMappingMemory, object_name: str, variant: str
) -> Tuple[List[SkipRule], List[ManualMapping]]:
    """Get effective skip rules and manual mappings for a specific table."""
    if not central_memory:
        return [], []

    # Start with global rules
    effective_skip_rules = central_memory.global_skip_fields.copy()
    effective_manual_mappings = central_memory.global_manual_mappings.copy()

    # Apply table-specific overrides
    table_key = f"{object_name}_{variant}"
    table_rules = central_memory.table_specific.get(table_key, {})

    # Add table-specific skip rules
    table_skip_data = table_rules.get("skip_fields", [])
    for skip_data in table_skip_data:
        effective_skip_rules.append(
            SkipRule(
                source_field=skip_data["source_field"],
                source_description=skip_data["source_description"],
                skip=skip_data["skip"],
                comment=skip_data["comment"],
            )
        )

    # Add table-specific manual mappings
    table_mapping_data = table_rules.get("manual_mappings", [])
    for mapping_data in table_mapping_data:
        effective_manual_mappings.append(
            ManualMapping(
                source_field=mapping_data["source_field"],
                source_description=mapping_data["source_description"],
                target=mapping_data["target"],
                target_description=mapping_data["target_description"],
                comment=mapping_data["comment"],
            )
        )

    return effective_skip_rules, effective_manual_mappings


def find_first_non_empty_worksheet(file_path: Path) -> str:
    """Find the first non-empty worksheet in an Excel file."""
    try:
        excel_file = pd.ExcelFile(file_path)
        for sheet_name in excel_file.sheet_names:
            # Read with no header row and as text to properly detect headers
            df = pd.read_excel(
                file_path,
                sheet_name=sheet_name,
                header=None,
                dtype=str,
                engine="openpyxl",
            )
            if not df.empty:
                # Check if any row has non-empty content
                def is_nonempty_row(r):
                    return any(
                        (str(x).strip() != "") for x in r.tolist() if x is not None
                    )

                if any(is_nonempty_row(row) for _, row in df.iterrows()):
                    return sheet_name
        raise ValueError("No non-empty worksheets found")
    except Exception as e:
        raise ValueError(f"Error reading Excel file: {e}")


def find_header_row(file_path: Path, sheet_name: str) -> Tuple[int, List[str]]:
    """Find the first row with ≥1 non-empty cell and return headers."""
    try:
        # Read Excel with no header row and as text
        df = pd.read_excel(
            file_path, sheet_name=sheet_name, header=None, dtype=str, engine="openpyxl"
        )

        def is_nonempty_row(r):
            return any((str(x).strip() != "") for x in r.tolist() if x is not None)

        # Find header row = first row with ≥1 non-empty cell after trimming
        header_idx = next(i for i, r in df.iterrows() if is_nonempty_row(r))

        # Build headers from that row
        headers = df.iloc[header_idx].fillna("").map(str).str.strip().tolist()

        return header_idx, headers
    except (StopIteration, Exception) as e:
        raise ValueError(f"Error finding header row: {e}")


def analyze_column_data(
    file_path: Path, sheet_name: str, header_row: int, headers: List[str]
) -> List[Dict]:
    """Analyze column data to infer types, nullable status, and examples."""
    try:
        # Read Excel with no header row and as text
        df = pd.read_excel(
            file_path, sheet_name=sheet_name, header=None, dtype=str, engine="openpyxl"
        )

        # Data rows may be zero
        data = df.iloc[header_row + 1 :].reset_index(drop=True)

        # Build source_fields even when data is empty
        source_fields = []
        field_count = 1
        for col_i, name in enumerate(headers, start=0):
            if name == "":
                continue  # Skip empty headers

            col = (
                data[col_i] if col_i in data.columns else pd.Series([], dtype="object")
            )
            col = col.astype(str).map(lambda s: s.strip()).replace({"": pd.NA})
            example = (col.dropna().head(1).tolist() or [None])[0]

            if example is None:
                dtype_val = "string"
                nullable = True  # unknown → assume nullable
            else:
                dtype_val = infer_dtype([example])
                nullable = col.isna().any()

            source_fields.append(
                {
                    "field_name": name,
                    "field_description": None,
                    "example": example,
                    "field_count": field_count,
                    "dtype": dtype_val,
                    "nullable": bool(nullable),
                }
            )
            field_count += 1

        return source_fields
    except Exception as e:
        raise ValueError(f"Error analyzing column data: {e}")


def apply_field_descriptions_from_central_memory(source_fields, central_memory, object_name, variant):
    """
    Apply field descriptions from central mapping memory for known fields.
    
    Args:
        source_fields: List of source field dictionaries
        central_memory: CentralMappingMemory instance
        object_name: Object name for table-specific rules
        variant: Variant name for table-specific rules
        
    Returns:
        List of enhanced source_fields with descriptions from central mapping memory
    """
    if not central_memory:
        return source_fields
    
    # Get effective rules for this table
    skip_rules, manual_mappings = get_effective_rules_for_table(
        central_memory, object_name, variant
    )
    
    # Create lookup dictionaries for fast matching
    skip_dict = {rule.source_field: rule for rule in skip_rules}
    manual_dict = {mapping.source_field: mapping for mapping in manual_mappings}
    
    enhanced_fields = []
    descriptions_applied = 0
    
    for field in source_fields:
        enhanced_field = field.copy()
        field_name = field.get("field_name", "")
        
        # Apply description from skip rules first (highest priority)
        if field_name in skip_dict:
            rule = skip_dict[field_name]
            enhanced_field["field_description"] = rule.source_description
            descriptions_applied += 1
        # Apply description from manual mappings
        elif field_name in manual_dict:
            mapping = manual_dict[field_name]
            enhanced_field["field_description"] = mapping.source_description
            descriptions_applied += 1
        
        enhanced_fields.append(enhanced_field)
    
    if descriptions_applied > 0:
        print(f"Applied {descriptions_applied} field descriptions from central mapping memory")
    
    return enhanced_fields


def apply_field_name_fallback(source_fields, central_memory, object_name, variant, enhanced_logger):
    """
    Apply fallback mechanism for missing or unclear field_names using global mapping rules.
    
    Args:
        source_fields: List of source field dictionaries
        central_memory: CentralMappingMemory instance
        object_name: Object name for table-specific rules
        variant: Variant name for table-specific rules
        enhanced_logger: EnhancedLogger for making fallback process visible
        
    Returns:
        List of enhanced source_fields with fallback field_names applied
    """
    if not central_memory:
        return source_fields
    
    # Get effective rules for this table
    table_key = f"{object_name}_{variant}"
    enhanced_fields = []
    fallbacks_applied = 0
    fallback_messages = []
    
    for field in source_fields:
        enhanced_field = field.copy()
        original_name = field.get("field_name", "")
        fallback_applied = False
        fallback_source = ""
        
        # Check if field_name is missing, empty, or seems unclear
        needs_fallback = (
            not original_name or 
            original_name.strip() == "" or
            original_name.lower() in ["unknown", "unnamed", "column", "field"] or
            original_name.startswith("Column") or
            original_name.startswith("Unnamed")
        )
        
        if needs_fallback:
            # Try to find fallback from global manual mappings first
            for mapping in central_memory.global_manual_mappings:
                # Match by example value, field description, or position
                field_example = str(field.get("example", "")).strip().upper()
                if (field_example and 
                    field_example in mapping.source_description.upper()):
                    enhanced_field["field_name"] = mapping.target
                    enhanced_field["field_description"] = f"Global fallback: {mapping.comment}"
                    fallback_applied = True
                    fallback_source = "global_manual_mapping"
                    break
            
            # Try table-specific manual mappings
            if not fallback_applied and table_key in central_memory.table_specific:
                table_rules = central_memory.table_specific[table_key]
                for mapping_data in table_rules.get("manual_mappings", []):
                    field_example = str(field.get("example", "")).strip().upper()
                    if (field_example and 
                        field_example in mapping_data.get("source_description", "").upper()):
                        enhanced_field["field_name"] = mapping_data["target"]
                        enhanced_field["field_description"] = f"Table fallback: {mapping_data['comment']}"
                        fallback_applied = True
                        fallback_source = "table_specific_mapping"
                        break
            
            # Try synonyms as fallback
            if not fallback_applied:
                field_example = str(field.get("example", "")).strip()
                for target_field, synonym_list in central_memory.synonyms.items():
                    for synonym in synonym_list:
                        if (field_example and 
                            synonym.lower() in field_example.lower()):
                            enhanced_field["field_name"] = target_field
                            enhanced_field["field_description"] = f"Synonym fallback: matched '{synonym}'"
                            fallback_applied = True
                            fallback_source = "synonyms"
                            break
                    if fallback_applied:
                        break
            
            # Last resort: mark as unknown but keep original
            if not fallback_applied:
                enhanced_field["field_name"] = original_name or f"Unknown_Field_{field.get('field_count', '')}"
                enhanced_field["field_description"] = "field_name onbekend - geen match in global mapping"
                fallback_source = "unknown_fallback"
        
        if fallback_applied:
            fallbacks_applied += 1
            # Make fallback process visible in CLI output/logging (using print for immediate visibility)
            fallback_messages.append(f"Field fallback applied: '{original_name}' -> '{enhanced_field['field_name']}' (via {fallback_source})")
        
        enhanced_fields.append(enhanced_field)
    
    # Make fallback process visible in CLI (explicit as requested)
    if fallbacks_applied > 0:
        print(f"Applied {fallbacks_applied} field name fallbacks using global mapping rules")
        for msg in fallback_messages:
            print(f"  {msg}")
    
    return enhanced_fields


def run_index_source_command(args, config):
    """Run the index_source command - parse headers from XLSX and create index_source.yaml."""
    from .enhanced_logging import EnhancedLogger

    warnings = []
    root_path = Path(args.root) if hasattr(args, "root") else Path(".")

    # Initialize enhanced logger
    logger = EnhancedLogger(args, "index_source", args.object, args.variant, root_path)

    try:
        # Construct input file path for index_source command (F01 spec: data/01_source/<object>_<variant>.xlsx)
        input_file = (
            root_path
            / config.input_dir
            / f"{args.object}_{args.variant}.xlsx"
        )

        # Check if input file exists
        if not input_file.exists():
            error_data = {"error": "missing_input", "path": str(input_file)}
            logger.log_error(error_data)
            sys.exit(2)

        # Find first non-empty worksheet
        try:
            sheet_name = find_first_non_empty_worksheet(input_file)
        except ValueError:
            error_data = {"error": "no_headers"}
            logger.log_error(error_data)
            sys.exit(3)

        # Find header row
        try:
            header_row_idx, headers = find_header_row(input_file, sheet_name)
        except ValueError:
            error_data = {"error": "no_headers"}
            logger.log_error(error_data)
            sys.exit(3)

        # Reject only if ALL headers are empty
        if all(h == "" for h in headers):
            error_data = {"error": "no_headers"}
            logger.log_error(error_data)
            sys.exit(3)

        # Filter out empty headers and warn about them
        processed_headers = []
        for i, header in enumerate(headers):
            if header.strip():
                processed_headers.append(header)
            elif header == "":
                warnings.append(f"Empty header found at column {i+1}")

        # Analyze column data
        try:
            source_fields = analyze_column_data(
                input_file, sheet_name, header_row_idx, processed_headers
            )
        except ValueError as e:
            error_data = {"error": "exception", "message": str(e)}
            logger.log_error(error_data)
            sys.exit(1)

        # Load central mapping memory for field name fallbacks and descriptions
        central_memory = load_central_mapping_memory(root_path)
        if central_memory:
            print("Loaded central mapping memory for field name fallbacks and descriptions")
            # Apply field descriptions from central mapping memory first
            source_fields = apply_field_descriptions_from_central_memory(
                source_fields, central_memory, args.object, args.variant
            )
            # Apply fallback mechanism for missing field_names
            source_fields = apply_field_name_fallback(
                source_fields, central_memory, args.object, args.variant, logger
            )

        # Create output directory structure
        migrations_dir = root_path / "migrations" / args.object / args.variant
        migrations_dir.mkdir(parents=True, exist_ok=True)

        # Check if output already exists and force flag
        output_file = migrations_dir / "index_source.yaml"
        force = getattr(args, "force", False)

        if output_file.exists() and not force:
            warnings.append(
                f"Output file exists and --force not specified: {output_file}"
            )
        else:
            # Create YAML structure with correct schema
            {
                "metadata": {
                    "object": args.object,
                    "variant": args.variant,
                    "source_file": str(input_file.relative_to(root_path)),
                    "generated_at": datetime.now().isoformat(),
                    "sheet": sheet_name,
                    "source_fields_count": len(source_fields),
                },
                "source_fields": source_fields,
            }

            # Write index_source.yaml with custom formatting
            with open(output_file, "w", encoding="utf-8") as f:
                # Write metadata section
                f.write("metadata:\n")
                f.write(f"  object: {args.object}\n")
                f.write(f"  variant: {args.variant}\n")
                f.write(f"  source_file: {input_file.relative_to(root_path)}\n")
                f.write(f"  generated_at: '{datetime.now().isoformat()}'\n")
                f.write(f"  sheet: {sheet_name}\n")
                f.write(f"  source_fields_count: {len(source_fields)}\n")

                # Add 3 empty lines between large blocks
                f.write("\n\n\n")

                # Write source_fields section
                f.write("source_fields:\n")
                for i, field in enumerate(source_fields):
                    if i > 0:
                        f.write("\n")  # Add 1 empty line between records
                    f.write(f"- field_name: {field['field_name']}\n")
                    f.write(f"  field_description: {field['field_description']}\n")
                    f.write(
                        f"  example: {repr(field['example']) if field['example'] is not None else 'null'}\n"
                    )
                    f.write(f"  field_count: {field['field_count']}\n")
                    f.write(f"  dtype: {field['dtype']}\n")
                    f.write(f"  nullable: {str(field['nullable']).lower()}\n")

        # Update global object list
        update_object_list(args.object, args.variant, root_path)

        # Prepare preview data for human output (first 8 headers)
        preview_data = []
        for i, field in enumerate(source_fields[:8]):
            preview_data.append(
                {
                    "field_name": field.get("field_name", ""),
                    "dtype": field.get("dtype", ""),
                    "nullable": field.get("nullable", True),
                    "example": field.get("example", ""),
                }
            )

        # Log summary
        total_columns = len([h for h in headers if h != ""])
        summary_data = {
            "step": "index_source",
            "object": args.object,
            "variant": args.variant,
            "input_file": str(input_file),
            "output_file": str(output_file),
            "total_columns": total_columns,
            "warnings": warnings,
        }
        
        # Generate HTML report if enabled
        if not getattr(args, 'no_html', False):
            from .reporting import write_html_report
            import json
            from datetime import datetime as dt
            
            timestamp = dt.now().strftime("%Y%m%d_%H%M")
            
            # Determine report directory for F01 (index_source) reports
            if hasattr(args, 'html_dir') and args.html_dir:
                reports_dir = Path(args.html_dir)
            else:
                reports_dir = root_path / "data" / "03_index_source"
            
            # Generate enriched summary for HTML report
            html_summary = {
                "step": "index_source",
                "object": args.object,
                "variant": args.variant,
                "ts": dt.now().isoformat(),
                "input_file": str(input_file.relative_to(root_path)),
                "sheet": sheet_name,
                "total_columns": total_columns,
                "headers": [
                    {
                        "index": i + 1,
                        "field_name": header,
                        "dtype": "string",  # Could be enhanced with actual dtype detection
                        "nullable": True,   # Could be enhanced with actual nullable detection
                        "example": None     # Could be enhanced with sample data
                    }
                    for i, header in enumerate([h for h in headers if h != ""])
                ],
                "duplicates": [h for h in headers if headers.count(h) > 1 and h != ""],
                "empty_headers": len([h for h in headers if h == ""]),
                "warnings": warnings
            }
            
            # Write JSON summary
            json_filename = f"index_source_{timestamp}.json"
            json_path = reports_dir / json_filename
            json_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(html_summary, f, ensure_ascii=False, indent=2)
            
            # Write HTML report
            html_filename = f"index_source_{timestamp}.html"
            html_path = reports_dir / html_filename
            title = f"index_source · {args.object}/{args.variant}"
            
            write_html_report(html_summary, html_path, title)
            
            # Human-readable logging with forward slashes
            html_path_display = str(html_path.relative_to(root_path)).replace('\\', '/')
            if not (args.json or not sys.stdout.isatty()):
                print(f"report: {html_path_display}")
        
        logger.log_event(summary_data, preview_data)

    except Exception as e:
        error_data = {"error": "exception", "message": str(e)}
        logger.log_error(error_data)
        sys.exit(1)


def _clean_xml_file(xml_path: Path) -> Path:
    """
    Clean XML file by removing comments and control characters.
    
    Args:
        xml_path: Path to original XML file
        
    Returns:
        Path to cleaned XML file (same path, with original backed up)
    """
    import re
    from lxml import etree
    
    # Create backup of original file
    backup_path = xml_path.with_name(f"{xml_path.stem}_original{xml_path.suffix}")
    xml_path.rename(backup_path)
    
    # Read original content
    with open(backup_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Remove XML comments
    content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
    
    # Remove control characters (except tabs, newlines, carriage returns)
    content = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', content)
    
    # Remove invalid attribute patterns like '&invalid;' and unclosed tags
    content = re.sub(r'&[a-zA-Z0-9]*;', '', content)
    content = re.sub(r'<[^/>]*\s+&[^>]*>', lambda m: m.group(0).split('&')[0] + '>', content)
    
    # Fix unclosed tags and invalid syntax
    content = re.sub(r'<([^/>]+)\s+&[^>]*>', r'<\1>', content)
    content = re.sub(r'</invalid>', '', content)
    content = re.sub(r'<invalid[^>]*>', '', content)
    
    # Write cleaned content to original path
    with open(xml_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return xml_path


def _parse_spreadsheetml_target_fields(
    xml_path: Path, variant: str
) -> List[Dict[str, Any]]:
    """
    Parse SpreadsheetML XML file according to F02 specification with robust error handling.

    Returns list of target field dictionaries with exact key ordering:
    ["sap_field","field_description","sap_table","mandatory","field_group","key","sheet_name","data_type","length","decimal"]
    """
    import xml.etree.ElementTree as ET
    from lxml import etree

    # Check if file contains comments or control characters that might cause issues
    with open(xml_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    has_comments = '<!--' in content
    has_control_chars = any(ord(c) < 32 and c not in '\t\n\r' for c in content)
    
    # Try parsing with standard library first
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        # If parsing succeeded but we detected comments/control chars, proactively clean
        if has_comments or has_control_chars:
            print("XML file contains comments or illegal characters. Old file is backed-up and cleaned.")
            _clean_xml_file(xml_path)
            # Re-parse the cleaned file
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
    except ET.ParseError as e:
        # If parsing fails, try with lxml's recovery parser
        try:
            parser = etree.XMLParser(recover=True)
            with open(xml_path, 'rb') as f:
                lxml_tree = etree.parse(f, parser)
            
            # Convert lxml tree to ElementTree for compatibility
            xml_string = etree.tostring(lxml_tree, encoding='unicode')
            root = ET.fromstring(xml_string)
            tree = None  # We don't need the tree object, just the root
        except Exception:
            # Last resort: clean the file and try again
            print("XML file contains comments or illegal characters. Old file is backed-up and cleaned.")
            cleaned_path = _clean_xml_file(xml_path)
            tree = ET.parse(cleaned_path)
            root = tree.getroot()

    # Define namespace
    ns = {"ss": "urn:schemas-microsoft-com:office:spreadsheet"}

    # Find the "Field List" worksheet
    worksheet = None
    for ws in root.findall(".//ss:Worksheet", ns):
        name = ws.get(f'{{{ns["ss"]}}}Name', "")
        if name == "Field List":
            worksheet = ws
            break

    if worksheet is None:
        raise ValueError("Worksheet 'Field List' not found")

    # Get worksheet name for fallback
    worksheet_name = worksheet.get(f'{{{ns["ss"]}}}Name', "")

    # Get all rows
    rows = worksheet.findall(".//ss:Row", ns)

    # Parse rows with ss:Index and ss:MergeDown support
    parsed_rows = []
    carry = {}  # For vertical propagation (ss:MergeDown)

    for row_idx, row in enumerate(rows):
        col = 1  # 1-based column pointer
        row_data = [None] * 15  # Pre-allocate for up to 15 columns

        # Apply carry-over values from previous rows
        for carry_col, carry_info in list(carry.items()):
            if carry_info["remaining"] > 0:
                row_data[carry_col - 1] = carry_info["value"]  # Convert to 0-based
                carry_info["remaining"] -= 1
                if carry_info["remaining"] == 0:
                    del carry[carry_col]

        # Process cells in this row
        for cell in row.findall("ss:Cell", ns):
            # Handle ss:Index (sparse cells)
            index_attr = cell.get(f'{{{ns["ss"]}}}Index')
            if index_attr:
                col = int(index_attr)

            # Extract cell value
            data_elem = cell.find("ss:Data", ns)
            cell_value = data_elem.text if data_elem is not None else None

            # Trim and convert empty to None
            if cell_value:
                cell_value = cell_value.strip()
                if not cell_value:
                    cell_value = None

            # Place value at current column (convert to 0-based)
            if col <= len(row_data):
                if col - 1 < len(row_data):
                    row_data[col - 1] = cell_value

            # Handle ss:MergeDown
            merge_down_attr = cell.get(f'{{{ns["ss"]}}}MergeDown')
            if merge_down_attr and cell_value is not None:
                merge_count = int(merge_down_attr)
                carry[col] = {"value": cell_value, "remaining": merge_count}

            col += 1

        parsed_rows.append(row_data)

    # Find header row - look for "Sheet Name" in any column
    header_row_idx = None
    for i, row_data in enumerate(parsed_rows):
        for cell in row_data:
            if cell and "Sheet Name" in str(cell):
                header_row_idx = i
                break
        if header_row_idx is not None:
            break

    if header_row_idx is None:
        raise ValueError("Header row with 'Sheet Name' not found")

    # Process data rows
    target_fields = []
    f"S_{variant.upper()}"
    field_count = 1

    for row_data in parsed_rows[header_row_idx + 1 :]:
        # Skip empty rows
        if not any(cell for cell in row_data if cell and str(cell).strip()):
            continue

        # Map columns according to specification:
        # Note: XML has ss:Index="2" for first column, so offset by 1
        # 2 "Sheet Name" → sheet_name
        # 3 "Group Name" → field_group
        # 4 "Field Description" → field_description
        # 5 "Importance" → mandatory (to bool)
        # 6 "Type" → data_type
        # 7 "Length" → length (int|null)
        # 8 "Decimal" → decimal (int|null)
        # 9 "SAP Structure" → sap_table (strip "S_")
        # 10 "SAP Field" → sap_field

        sheet_name = row_data[1] if len(row_data) > 1 else None  # Column 2 -> index 1
        field_group_raw = (
            row_data[2] if len(row_data) > 2 else None
        )  # Column 3 -> index 2
        field_description = (
            row_data[3] if len(row_data) > 3 else None
        )  # Column 4 -> index 3
        importance_raw = (
            row_data[4] if len(row_data) > 4 else None
        )  # Column 5 -> index 4
        data_type = row_data[5] if len(row_data) > 5 else None  # Column 6 -> index 5
        length_raw = row_data[6] if len(row_data) > 6 else None  # Column 7 -> index 6
        decimal_raw = row_data[7] if len(row_data) > 7 else None  # Column 8 -> index 7
        sap_table_raw = (
            row_data[8] if len(row_data) > 8 else None
        )  # Column 9 -> index 8
        sap_field_raw = (
            row_data[9] if len(row_data) > 9 else None
        )  # Column 10 -> index 9

        # Apply sheet_name fallback
        if not sheet_name:
            sheet_name = worksheet_name

        # Filter: only rows where column 8 starts with "S_" and matches variant
        if not sap_table_raw or not str(sap_table_raw).startswith("S_"):
            continue

        # Check if matches variant (case-insensitive)
        sap_table_clean = str(sap_table_raw)[2:].lower()  # Remove "S_" and lowercase
        if sap_table_clean != variant.lower():
            continue

        # Normalize fields
        # field_group: lower(); if equals "key" then key=true else false
        field_group = field_group_raw.lower() if field_group_raw else ""
        key = field_group == "key"

        # mandatory: true if contains "mandatory" or in {"X","x","true","1"}
        mandatory = False
        if importance_raw:
            importance_str = str(importance_raw).lower()
            mandatory = "mandatory" in importance_str or importance_str in {
                "x",
                "true",
                "1",
            }

        # length, decimal: parse int; invalid → None
        length = None
        if length_raw:
            try:
                length = int(str(length_raw).strip())
            except (ValueError, AttributeError):
                length = None

        decimal = None
        if decimal_raw:
            try:
                decimal = int(str(decimal_raw).strip())
            except (ValueError, AttributeError):
                decimal = None

        # sap_table: strip prefix "S_"/"s_", then lower
        sap_table = sap_table_raw[2:].lower() if sap_table_raw else ""

        # sap_field: lower
        sap_field = sap_field_raw.lower() if sap_field_raw else ""

        # Skip rows without required sap_field
        if not sap_field:
            continue

        # Build row dict with EXACT key ordering
        row_dict = {}
        row_dict["sap_field"] = sap_field
        row_dict["field_description"] = field_description
        row_dict["sap_table"] = sap_table
        row_dict["mandatory"] = mandatory
        row_dict["field_group"] = field_group
        row_dict["key"] = key
        row_dict["sheet_name"] = sheet_name
        row_dict["data_type"] = data_type
        row_dict["length"] = length
        row_dict["decimal"] = decimal
        row_dict["field_count"] = field_count

        target_fields.append(row_dict)
        field_count += 1

    return target_fields


def run_index_target_command(args, config):
    """Run the index_target command - parse XML and filter target fields by variant."""
    from .enhanced_logging import EnhancedLogger
    from datetime import datetime
    from pathlib import Path

    root_path = Path(args.root).resolve()

    # Initialize enhanced logger
    logger = EnhancedLogger(args, "index_target", args.object, args.variant, root_path)

    # Construct input file path - check both .xml and fallback formats (F02 spec: data/02_target/{object}_{variant}.xml)
    xml_file = (
        root_path / f"data/02_target/{args.object}_{args.variant}.xml"
    )
    
    input_file = xml_file
    xml_parse_error = None
    
    # Check if --prefer-xlsx flag is set
    prefer_xlsx = getattr(args, 'prefer_xlsx', False)
    
    # If prefer-xlsx is set, try xlsx first
    if prefer_xlsx:
        xlsx_file = (
            root_path / f"data/02_target/{args.object}_{args.variant}.xlsx"
        )
        if xlsx_file.exists():
            input_file = xlsx_file
            print(f"Using {xlsx_file.name} as target definition (--prefer-xlsx enabled).")
        else:
            input_file = None  # Force fallback search
    else:
        # Check if XML file exists and can be parsed
        if xml_file.exists():
            try:
                # Try to parse XML to validate it's readable
                _parse_spreadsheetml_target_fields(xml_file, args.variant)
                # If successful, use XML file
                input_file = xml_file
            except Exception as e:
                # XML exists but has parsing errors - record for fallback
                xml_parse_error = str(e)
                print(f"Warning: XML parsing failed for {xml_file}: {xml_parse_error}")
                input_file = None  # Force fallback search
        else:
            input_file = None  # XML doesn't exist, search for fallbacks

    # Check for fallback files if XML doesn't exist or has parse errors or --prefer-xlsx was set but xlsx not found
    if input_file is None:
        xlsx_file = (
            root_path / f"data/02_target/{args.object}_{args.variant}.xlsx"
        )
        json_file = (
            root_path / f"data/02_target/{args.object}_{args.variant}.json"
        )
        yaml_file = (
            root_path / f"data/02_target/{args.object}_{args.variant}.yaml"
        )

        if xlsx_file.exists():
            input_file = xlsx_file
            if xml_file.exists():
                print(f"Fallback: {xml_file.name} parsing failed, using {xlsx_file.name} as target definition.")
            else:
                print(f"Fallback: {xml_file.name} not found, using {xlsx_file.name} as target definition.")
        elif json_file.exists():
            input_file = json_file
        elif yaml_file.exists():
            input_file = yaml_file
        else:
            error_msg = f"No usable input files found. Searched for: {xml_file.name}"
            if xml_parse_error:
                error_msg += f" (parse error: {xml_parse_error})"
            error_msg += f", {xlsx_file.name}, {json_file.name}, {yaml_file.name}"
            error_data = {"error": "missing_input", "path": str(xml_file), "message": error_msg}
            logger.log_error(error_data)
            sys.exit(2)

    # Create output directory structure
    output_dir = root_path / f"migrations/{args.object}/{args.variant}"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "index_target.yaml"

    # Check overwrite policy
    if output_file.exists() and not args.force:
        error_data = {"error": "would_overwrite", "path": str(output_file)}
        logger.log_error(error_data)
        sys.exit(5)

    try:
        if input_file.suffix == ".xml":
            target_fields = _parse_spreadsheetml_target_fields(input_file, args.variant)
        elif input_file.suffix == ".xlsx":
            # Import xlsx parser
            from .parsers import read_excel_target_fields
            target_fields = read_excel_target_fields(input_file, args.variant)
        else:
            # Handle JSON/YAML fallback (simplified for now)
            error_data = {"error": "unsupported_format", "path": str(input_file)}
            logger.log_error(error_data)
            sys.exit(1)

        if not target_fields:
            error_data = {"error": "structure_not_found", "variant": args.variant}
            logger.log_error(error_data)
            sys.exit(3)

        # Create output YAML structure with exact metadata schema
        {
            "metadata": {
                "object": args.object,
                "variant": args.variant,
                "target_file": f"data/02_target/{args.object}_{args.variant}.xml",
                "generated_at": datetime.now().isoformat(),
                "structure": f"S_{args.variant.upper()}",
                "target_fields_count": len(target_fields),
            },
            "target_fields": target_fields,
        }

        # Write index_target.yaml with custom formatting
        with open(output_file, "w", encoding="utf-8") as f:
            # Write metadata section
            f.write("metadata:\n")
            f.write(f"  object: {args.object}\n")
            f.write(f"  variant: {args.variant}\n")
            f.write(
                f"  target_file: {input_file.relative_to(root_path)}\n"
            )
            f.write(f"  generated_at: '{datetime.now().isoformat()}'\n")
            f.write(f"  structure: S_{args.variant.upper()}\n")
            f.write(f"  target_fields_count: {len(target_fields)}\n")

            # Add 3 empty lines between large blocks
            f.write("\n\n\n")

            # Write target_fields section
            f.write("target_fields:\n")
            for i, field in enumerate(target_fields):
                if i > 0:
                    f.write("\n")  # Add 1 empty line between records
                f.write(f"- sap_field: {field['sap_field']}\n")
                f.write(f"  field_description: {field['field_description']}\n")
                f.write(f"  sap_table: {field['sap_table']}\n")
                f.write(f"  mandatory: {str(field['mandatory']).lower()}\n")
                f.write(f"  field_group: {field['field_group']}\n")
                f.write(f"  key: {str(field['key']).lower()}\n")
                f.write(f"  sheet_name: {field['sheet_name']}\n")
                f.write(f"  data_type: {field['data_type']}\n")
                f.write(f"  length: {field['length']}\n")
                f.write(f"  decimal: {field['decimal']}\n")
                f.write(f"  field_count: {field['field_count']}\n")

        # Generate validation.yaml scaffold
        validation_file = output_dir / "validation.yaml"
        validation_warnings = []

        # Check overwrite policy for validation.yaml
        validation_created = "created"
        if validation_file.exists() and not args.force:
            validation_created = "skipped:exists"
            validation_warnings.append(
                {
                    "warning": "validation_exists",
                    "message": f"validation.yaml exists, use --force to overwrite: {validation_file}",
                }
            )
        else:
            # Generate validation scaffold
            validation_rules = []
            has_decimals = False

            for field in target_fields:
                base_field = field["sap_field"].upper()
                key = field.get("key", False)
                mandatory = field.get("mandatory", False)
                data_type = field.get("data_type", "")
                length = field.get("length")
                decimal = field.get("decimal")

                # Handle conflict guard: key=true implies required=true
                required = mandatory or key
                if key and not mandatory:
                    validation_warnings.append(
                        {"warning": "key_implies_required", "field": base_field}
                    )

                # Type inference from data_type
                field_type = "string"  # default
                if data_type:
                    data_type_upper = data_type.upper()
                    if "DATE" in data_type_upper:
                        field_type = "date"
                    elif "TIME" in data_type_upper:
                        field_type = "time"
                    elif (
                        "NUM" in data_type_upper
                        or "DEC" in data_type_upper
                        or decimal is not None
                    ):
                        field_type = "decimal"
                        if decimal is not None:
                            has_decimals = True

                # Build validation rule with fixed key order
                rule = {
                    "field": base_field,
                    "key": key,
                    "required": required,
                    "type": field_type,
                }

                # Add max_length only if length is a valid integer
                if length is not None:
                    try:
                        max_length = int(length)
                        rule["max_length"] = max_length
                    except (ValueError, TypeError):
                        pass  # omit max_length when invalid

                validation_rules.append(rule)

            # Write validation.yaml with custom formatting
            with open(validation_file, "w", encoding="utf-8") as f:
                # Write metadata section
                f.write("metadata:\n")
                f.write(f"  object: {args.object}\n")
                f.write(f"  variant: {args.variant}\n")
                f.write(
                    f"  target_file: data/02_target/{args.object}_{args.variant}.xml\n"
                )
                f.write(f"  generated_at: '{datetime.now().isoformat()}'\n")
                f.write(f"  structure: S_{args.variant.upper()}\n")
                f.write("\n\n\n")  # Add 3 blank lines after metadata

                # Write validation section
                f.write("validation:\n")
                for i, rule in enumerate(validation_rules):
                    if i > 0:
                        f.write("\n")  # Add blank line between validation records
                    f.write(f"- field: {rule['field']}\n")
                    f.write(f"  key: {str(rule['key']).lower()}\n")
                    f.write(f"  required: {str(rule['required']).lower()}\n")
                    f.write(f"  type: {rule['type']}\n")
                    if "max_length" in rule:
                        f.write(f"  max_length: {rule['max_length']}\n")

                # Add numeric_defaults section only if any field has decimals
                if has_decimals:
                    f.write("\n\nnumeric_defaults:\n")
                    f.write('  decimal_separator: "."\n')
                    f.write('  thousands_separator: ""\n')

        # Prepare preview data for human output (first 8 fields)
        preview_data = []
        for field in target_fields[:8]:
            preview_data.append(
                {
                    "sap_field": field.get("sap_field", ""),
                    "field_description": field.get("field_description", ""),
                    "mandatory": field.get("mandatory", False),
                    "data_type": field.get("data_type", ""),
                    "length": field.get("length", ""),
                    "decimal": field.get("decimal", ""),
                    "field_group": field.get("field_group", ""),
                    "key": field.get("key", False),
                }
            )

        # Log summary with validation scaffold info
        summary_data = {
            "step": "index_target",
            "object": args.object,
            "variant": args.variant,
            "input_file": str(input_file),
            "output_file": str(output_file),
            "structure": f"S_{args.variant.upper()}",
            "total_fields": len(target_fields),
            "validation_scaffold": f"migrations/{args.object}/{args.variant}/validation.yaml",
            "rules_count": (
                len(validation_rules) if validation_created == "created" else 0
            ),
            "warnings": validation_warnings,
        }
        
        # Generate HTML report if enabled
        if not getattr(args, 'no_html', False):
            from .reporting import write_html_report
            import json
            from datetime import datetime as dt
            
            timestamp = dt.now().strftime("%Y%m%d_%H%M")
            
            # Determine report directory for F02 (index_target) reports
            if hasattr(args, 'html_dir') and args.html_dir:
                reports_dir = Path(args.html_dir)
            else:
                reports_dir = root_path / "data" / "04_index_target"
            
            # Count field groups for chart data
            field_groups = {}
            mandatory_count = 0
            key_count = 0
            
            for field in target_fields:
                group = field.get("field_group", "unknown")
                field_groups[group] = field_groups.get(group, 0) + 1
                if field.get("mandatory", False):
                    mandatory_count += 1
                if field.get("key", False):
                    key_count += 1
            
            # Check for enforced 10-key rule
            order_ok = key_count == 10
            
            # Generate enriched summary for HTML report
            html_summary = {
                "step": "index_target",
                "object": args.object,
                "variant": args.variant,
                "structure": f"S_{args.variant.upper()}",
                "ts": dt.now().isoformat(),
                "input_file": str(input_file.relative_to(root_path)),
                "total_fields": len(target_fields),
                "mandatory": mandatory_count,
                "keys": key_count,
                "groups": field_groups,
                "order_ok": order_ok,
                "sample_fields": [
                    {
                        "sap_field": field.get("sap_field", ""),
                        "sap_table": field.get("sap_table", ""),
                        "mandatory": field.get("mandatory", False),
                        "key": field.get("key", False),
                        "data_type": field.get("data_type", ""),
                        "length": field.get("length", ""),
                        "decimal": field.get("decimal", "")
                    }
                    for field in target_fields
                ],
                "anomalies": [],  # Could be enhanced with anomaly detection
                "validation_scaffold": {
                    "created": validation_created == "created",
                    "path": f"migrations/{args.object}/{args.variant}/validation.yaml",
                    "rules_count": len(validation_rules) if validation_created == "created" else 0
                },
                "warnings": validation_warnings
            }
            
            # Write JSON summary
            json_filename = f"index_target_{timestamp}.json"
            json_path = reports_dir / json_filename
            json_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(html_summary, f, ensure_ascii=False, indent=2)
            
            # Write HTML report
            html_filename = f"index_target_{timestamp}.html"
            html_path = reports_dir / html_filename
            title = f"index_target · S_{args.variant.upper()} · {args.object}/{args.variant}"
            
            write_html_report(html_summary, html_path, title)
            
            # Human-readable logging with forward slashes
            html_path_display = str(html_path.relative_to(root_path)).replace('\\', '/')
            if not (args.json or not sys.stdout.isatty()):
                print(f"report: {html_path_display}")
        
        logger.log_event(summary_data, preview_data)

    except Exception as e:
        error_data = {"error": "exception", "message": str(e)}
        logger.log_error(error_data)
        sys.exit(1)


def update_object_list(object_name: str, variant: str, root_path: Path = None):
    """Update or create the global object_list.yaml file."""
    if root_path is None:
        root_path = Path(".")

    object_list_file = root_path / "migrations" / "object_list.yaml"

    # Load existing data if file exists
    object_list_data = {"entries": []}
    if object_list_file.exists():
        try:
            with open(object_list_file, "r", encoding="utf-8") as f:
                existing_data = yaml.safe_load(f)
                if existing_data and "entries" in existing_data:
                    object_list_data = existing_data
        except Exception:
            pass  # Use default structure if file is corrupted

    # Check if this object/variant combination already exists
    existing_entries = []
    for entry in object_list_data["entries"]:
        if entry.get("object") == object_name and entry.get("variant") == variant:
            existing_entries.append(entry)

    if not existing_entries:
        new_entry = {
            "object": object_name,
            "variant": variant,
            "added_at": datetime.now().isoformat(),
        }
        object_list_data["entries"].append(new_entry)

        # Write updated object list
        object_list_file.parent.mkdir(parents=True, exist_ok=True)
        with open(object_list_file, "w", encoding="utf-8") as f:
            yaml.dump(object_list_data, f, default_flow_style=False, allow_unicode=True)


def apply_central_memory_to_unmapped_fields(mapping_result, central_memory, object_name, variant):
    """
    Post-process unmapped source fields to apply central mapping memory context.
    
    Args:
        mapping_result: Result from process_f03_mapping
        central_memory: CentralMappingMemory instance
        object_name: Object name for table-specific rules
        variant: Variant name for table-specific rules
        
    Returns:
        Enhanced mapping_result with detailed unmapped field information
    """
    if not central_memory:
        return mapping_result
    
    # Get effective rules for this table
    skip_rules, manual_mappings = get_effective_rules_for_table(
        central_memory, object_name, variant
    )
    
    # Create lookup dictionaries
    skip_dict = {rule.source_field: rule for rule in skip_rules if rule.skip}
    manual_dict = {mapping.source_field: mapping for mapping in manual_mappings}
    
    # Transform simple unmapped field names to detailed objects
    enhanced_unmapped_fields = []
    
    for field_name in mapping_result["unmapped_source_fields"]:
        if field_name in skip_dict:
            # This field is configured to be skipped
            rule = skip_dict[field_name]
            enhanced_unmapped_fields.append({
                "source_field_name": field_name,
                "source_field_description": rule.source_description,
                "confidence": 1.0,
                "rationale": "Global skip field configured in central mapping memory",
                "comment": rule.comment,
                "required": False,
                "source_header": None,
                "status": "unmapped",
                "target_field": None,
                "target_table": None
            })
        elif field_name in manual_dict:
            # This field has a manual mapping but wasn't used (might be unmapped target)
            mapping = manual_dict[field_name]
            enhanced_unmapped_fields.append({
                "source_field_name": field_name,
                "source_field_description": mapping.source_description,
                "confidence": 0.0,
                "rationale": "Manual mapping configured but target not found",
                "comment": mapping.comment,
                "required": False,
                "source_header": None,
                "status": "unmapped",
                "target_field": mapping.target,
                "target_table": None
            })
        else:
            # Regular unmapped field - keep as simple string for now
            # Could be enhanced further if needed
            enhanced_unmapped_fields.append(field_name)
    
    # Update the mapping result
    mapping_result["unmapped_source_fields"] = enhanced_unmapped_fields
    
    return mapping_result


def process_f03_mapping(source_fields, target_fields, synonyms, object_name, variant):
    """
    Process mapping according to F03 specification.

    Args:
        source_fields: List of source field dicts with field_name, dtype, nullable, example
        target_fields: List of target field dicts with exact 10 keys in F02 order
        synonyms: Dict of synonym mappings from central_mapping_memory.yaml
        object_name: Object name for transformer_id generation
        variant: Variant name for transformer_id generation

    Returns:
        Dict with metadata, mappings, to_audit, unmapped_source_fields, unmapped_target_fields
    """
    from datetime import datetime
    from .fuzzy import FieldNormalizer, FuzzyMatcher

    # Helper function for tiebreakers (as per spec: longest common substring, then shortest source header)
    def is_better_match(candidate, current_best, target_name):
        if not current_best:
            return True

        # Longest common substring
        def longest_common_substring(s1, s2):
            if not s1 or not s2:
                return 0
            max_len = 0
            for i in range(len(s1)):
                for j in range(i + 1, len(s1) + 1):
                    substr = s1[i:j]
                    if substr in s2:
                        max_len = max(max_len, len(substr))
            return max_len

        candidate_lcs = longest_common_substring(candidate.lower(), target_name.lower())
        current_lcs = longest_common_substring(
            current_best.lower(), target_name.lower()
        )

        if candidate_lcs > current_lcs:
            return True
        elif candidate_lcs == current_lcs:
            # Tie in LCS, use shortest header
            return len(candidate) < len(current_best)
        return False

    def norm(s):
        if not s:
            return ""
        # lower → non-alphanumeric to space → collapse spaces → strip
        import re

        lowered = s.lower()
        spaces = re.sub(r"[^a-zA-Z0-9]", " ", lowered)
        collapsed = re.sub(r"\s+", " ", spaces)
        return collapsed.strip()

    # Extract verbatim and normalized headers, creating a lookup map for field names
    verbatim_headers = [field.get("field_name", "") for field in source_fields]
    [norm(header) for header in verbatim_headers]
    
    # Create lookup map from header to source field for preserving field_name information
    header_to_field = {field.get("field_name", ""): field for field in source_fields}

    # Create fuzzy matcher components
    normalizer = FieldNormalizer()
    fuzzy_matcher = FuzzyMatcher()

    # Initialize result structures
    mappings = []
    to_audit = []
    unmapped_source_fields = []
    unmapped_target_fields = []
    used_sources = set()
    reused_sources = {}  # Track sources used multiple times

    # Process each target field (target-centric approach)
    for target in target_fields:
        t_name = target.get("sap_field", "").lower()
        t_desc = (target.get("field_description") or "").lower()
        t_table = target.get("sap_table", "").lower()
        required = bool(target.get("mandatory", False))

        best_match = None
        best_confidence = 0.0
        best_rationale = "none"
        candidates = []  # For tie-break detection

        # 1. EXACT MATCH: norm(header) == t_name
        for i, header in enumerate(verbatim_headers):
            if norm(header) == t_name:
                best_match = header
                best_confidence = 1.00
                best_rationale = "Exact field name match"
                break

        # 2. SYNONYM MATCH: if no exact match and synonyms available
        if not best_match and synonyms:
            t_name_upper = t_name.upper()
            if t_name_upper in synonyms:
                synonym_variants = synonyms[t_name_upper]
                for i, header in enumerate(verbatim_headers):
                    if norm(header) in [norm(variant) for variant in synonym_variants]:
                        best_match = header
                        best_confidence = 0.95
                        best_rationale = "Matched via synonym definition"
                        break

        # 3. FUZZY MATCH: against t_name and t_desc
        if not best_match:
            for i, header in enumerate(verbatim_headers):
                norm_header = normalizer.normalize_field_name(header)

                # Try against target field name
                name_score = 0.0
                if t_name:
                    norm_target_name = normalizer.normalize_field_name(t_name)
                    lev_sim = fuzzy_matcher.levenshtein_similarity(
                        norm_header, norm_target_name
                    )
                    jw_sim = fuzzy_matcher.jaro_winkler_similarity(
                        norm_header, norm_target_name
                    )
                    name_score = max(lev_sim, jw_sim)

                # Try against target description
                desc_score = 0.0
                if t_desc:
                    norm_target_desc = normalizer.normalize_field_name(t_desc)
                    lev_sim = fuzzy_matcher.levenshtein_similarity(
                        norm_header, norm_target_desc
                    )
                    jw_sim = fuzzy_matcher.jaro_winkler_similarity(
                        norm_header, norm_target_desc
                    )
                    desc_score = max(lev_sim, jw_sim)

                # Take the maximum score from name and description matching
                score = max(name_score, desc_score)

                # Apply thresholds per spec
                if score >= 0.85:
                    if score > best_confidence or (
                        score == best_confidence
                        and is_better_match(header, best_match, t_name)
                    ):
                        best_match = header
                        best_confidence = score
                        best_rationale = f"Fuzzy match with {score:.0%} confidence"
                    candidates.append((header, score))
                elif 0.80 <= score < 0.85 and required:
                    # Only map if target is mandatory
                    if score > best_confidence or (
                        score == best_confidence
                        and is_better_match(header, best_match, t_name)
                    ):
                        best_match = header
                        best_confidence = score
                        best_rationale = (
                            f"Fuzzy match with {score:.0%} confidence (mandatory field)"
                        )
                    candidates.append((header, score))

        # Handle tiebreakers (tie when delta score <= 0.02)
        candidates.sort(key=lambda x: x[1], reverse=True)
        if len(candidates) > 1 and abs(candidates[0][1] - candidates[1][1]) <= 0.02:
            # Tie detected - add to audit with field_name
            tie_field_name = "field_name onbekend"
            if best_match and best_match in header_to_field:
                tie_field_name = header_to_field[best_match].get("field_name", "field_name onbekend")
            
            to_audit.append(
                {
                    "target_table": t_table,
                    "target_field": t_name.upper(),  # Make target_field uppercase for SAP compliance
                    "source_header": best_match,
                    "source_field_name": tie_field_name,
                    "confidence": best_confidence,
                    "reason": "tie_break",
                }
            )

        # Create mapping entry
        status = "auto" if best_match else "unmapped"
        # Set appropriate rationale for unmapped fields
        if not best_match:
            best_rationale = "Added without source match, to comply with SAP template"

        # Always include field_name - via input, global fallback, or explicit unknown
        source_field_name = "field_name onbekend"
        source_field_description = None
        if best_match and best_match in header_to_field:
            source_field = header_to_field[best_match]
            source_field_name = source_field.get("field_name", "field_name onbekend")
            source_field_description = source_field.get("field_description")
        elif not best_match:
            source_field_name = "field_name onbekend"

        mapping = {
            "target_table": t_table,
            "target_field": t_name.upper(),  # Make target_field uppercase for SAP compliance
            "source_header": best_match,
            "source_field_name": source_field_name,  # Always show field_name
            "source_field_description": source_field_description,
            "required": required,
            "confidence": round(best_confidence, 2),
            "status": status,
            "rationale": best_rationale,
        }
        mappings.append(mapping)

        # Track source usage for reuse detection
        if best_match:
            if best_match in used_sources:
                if best_match not in reused_sources:
                    reused_sources[best_match] = []
                reused_sources[best_match].append(mapping)
            else:
                used_sources.add(best_match)

        # Add to audit based on conditions
        if best_match:
            # Get field_name for audit entries
            audit_field_name = "field_name onbekend"
            if best_match in header_to_field:
                audit_field_name = header_to_field[best_match].get("field_name", "field_name onbekend")
            
            # Low confidence fuzzy
            if 0.80 <= best_confidence < 0.90:
                to_audit.append(
                    {
                        "target_table": t_table,
                        "target_field": t_name.upper(),  # Make target_field uppercase for SAP compliance
                        "source_header": best_match,
                        "source_field_name": audit_field_name,
                        "confidence": best_confidence,
                        "reason": "low_confidence_fuzzy",
                    }
                )

            # Synonym based
            if best_rationale == "Matched via synonym definition":
                to_audit.append(
                    {
                        "target_table": t_table,
                        "target_field": t_name.upper(),  # Make target_field uppercase for SAP compliance
                        "source_header": best_match,
                        "source_field_name": audit_field_name,
                        "confidence": best_confidence,
                        "reason": "synonym_based",
                    }
                )
        else:
            # Required unmapped
            if required:
                to_audit.append(
                    {
                        "target_table": t_table,
                        "target_field": t_name.upper(),  # Make target_field uppercase for SAP compliance
                        "source_header": None,
                        "source_field_name": "field_name onbekend",
                        "confidence": 0.00,
                        "reason": "required_unmapped",
                    }
                )

            # Add to unmapped targets
            unmapped_target_fields.append(
                {
                    "target_table": t_table,
                    "target_field": t_name.upper(),  # Make target_field uppercase for SAP compliance
                    "required": required,
                }
            )

    # Handle reused sources audit
    for source_header, mappings_list in reused_sources.items():
        for mapping in mappings_list:
            to_audit.append(
                {
                    "target_table": mapping["target_table"],
                    "target_field": mapping["target_field"],
                    "source_header": source_header,
                    "confidence": mapping["confidence"],
                    "reason": "reused_source",
                }
            )

    # Find unmapped source fields
    unmapped_source_fields = [
        header for header in verbatim_headers if header not in used_sources
    ]

    # Create metadata
    metadata = {
        "object": object_name,
        "variant": variant,
        "generated_at": datetime.now().isoformat(),
        "source_index": f"migrations/{object_name}/{variant}/index_source.yaml",
        "target_index": f"migrations/{object_name}/{variant}/index_target.yaml",
    }

    return {
        "metadata": metadata,
        "mappings": mappings,
        "to_audit": to_audit,
        "unmapped_source_fields": unmapped_source_fields,
        "unmapped_target_fields": unmapped_target_fields,
    }


def run_map_command(args, config):
    """Run the map command - generates mapping from indexed source and target YAML files."""
    from .enhanced_logging import EnhancedLogger
    import time

    start_time = time.time()
    
    # Set up paths using root directory
    root_path = Path(args.root)
    
    # Initialize enhanced logger
    logger = EnhancedLogger(args, "map", args.object, args.variant, root_path)
    migrations_dir = root_path / "migrations" / args.object / args.variant
    source_index_file = migrations_dir / "index_source.yaml"
    target_index_file = migrations_dir / "index_target.yaml"
    mapping_file = migrations_dir / "mapping.yaml"

    # Central mapping memory (optional)
    central_mapping_file = root_path / "config" / "central_mapping_memory.yaml"
    if not central_mapping_file.exists():
        central_mapping_file = root_path / "central_mapping_memory.yaml"

    # Check for required files with proper exit codes
    if not source_index_file.exists():
        error_data = {
            "error": "missing_input",
            "path": str(source_index_file),
        }
        logger.log_error(error_data)
        sys.exit(2)

    if not target_index_file.exists():
        error_data = {
            "error": "missing_input",
            "path": str(target_index_file),
        }
        logger.log_error(error_data)
        sys.exit(3)

    # Check if output exists and enforce --force policy
    if mapping_file.exists() and not args.force:
        error_data = {
            "error": "would_overwrite",
            "path": str(mapping_file),
        }
        logger.log_error(error_data)
        sys.exit(5)

    try:
        # Load source fields
        with open(source_index_file, "r", encoding="utf-8") as f:
            source_data = yaml.safe_load(f)

        # Load target fields
        with open(target_index_file, "r", encoding="utf-8") as f:
            target_data = yaml.safe_load(f)

        source_fields = source_data.get("source_fields", [])
        target_fields = target_data.get("target_fields", [])

        if not target_fields:
            error_data = {
                "error": "exception",
                "message": "No target fields found in index_target.yaml",
            }
            logger.log_error(error_data)
            sys.exit(4)

        # Load central mapping memory (full) if available
        central_memory = load_central_mapping_memory(root_path)
        synonyms = {}
        if central_memory:
            synonyms = central_memory.synonyms
        elif central_mapping_file.exists():
            try:
                with open(central_mapping_file, "r", encoding="utf-8") as f:
                    central_data = yaml.safe_load(f)
                    synonyms = central_data.get("synonyms", {})
            except Exception:
                pass  # Continue without synonyms if file is corrupted

        # Process mapping according to F03 specification
        mapping_result = process_f03_mapping(
            source_fields, target_fields, synonyms, args.object, args.variant
        )

        # Post-process unmapped source fields with central mapping memory context
        if central_memory:
            mapping_result = apply_central_memory_to_unmapped_fields(
                mapping_result, central_memory, args.object, args.variant
            )

        # Calculate metrics for metadata
        mapped_count = len(
            [m for m in mapping_result["mappings"] if m["status"] == "auto"]
        )
        unmapped_count = len(mapping_result["unmapped_target_fields"])
        to_audit_count = len(mapping_result["to_audit"])
        unused_sources_count = len(mapping_result["unmapped_source_fields"])
        unused_targets_count = 0  # As specified in the requirement

        # Add metrics to metadata
        mapping_result["metadata"]["mapped_count"] = mapped_count
        mapping_result["metadata"]["unmapped_count"] = unmapped_count
        mapping_result["metadata"]["to_audit"] = to_audit_count
        mapping_result["metadata"]["unused_sources"] = unused_sources_count
        mapping_result["metadata"]["unused_targets"] = unused_targets_count

        # Create output structure with exact key ordering
        output_data = {
            "metadata": mapping_result["metadata"],
            "mappings": mapping_result["mappings"],
            "to_audit": mapping_result["to_audit"],
            "unmapped_source_fields": mapping_result["unmapped_source_fields"],
            "unmapped_target_fields": mapping_result["unmapped_target_fields"],
        }

        # Write mapping.yaml with exact format and proper blank lines
        mapping_file.parent.mkdir(parents=True, exist_ok=True)
        with open(mapping_file, "w", encoding="utf-8") as f:
            # Write metadata section
            yaml.safe_dump(
                {"metadata": output_data["metadata"]},
                f,
                sort_keys=False,
                allow_unicode=True,
                default_flow_style=False,
            )

            # Add 3 blank lines between sections
            f.write("\n\n\n")

            # Write mappings section with special formatting (1 blank line between records)
            f.write("mappings:\n")
            for i, mapping in enumerate(output_data["mappings"]):
                # Write each mapping item with proper indentation
                mapping_yaml = yaml.safe_dump(
                    [mapping], default_flow_style=False, allow_unicode=True
                )
                # Process the YAML lines correctly to maintain proper structure
                lines = mapping_yaml.strip().split("\n")
                for j, line in enumerate(lines):
                    if j == 0:
                        # First line: ensure it starts with "- " for list item
                        if line.startswith("- "):
                            f.write(line + "\n")
                        else:
                            f.write("- " + line + "\n")
                    else:
                        # Subsequent lines: maintain proper 2-space indentation for list item content
                        if line.startswith("  "):
                            f.write(line + "\n")
                        else:
                            f.write("  " + line + "\n")

                # Add blank line between mapping records (except after the last one)
                if i < len(output_data["mappings"]) - 1:
                    f.write("\n")

            # Add 3 blank lines before next section
            f.write("\n\n\n")

            # Write to_audit section
            yaml.safe_dump(
                {"to_audit": output_data["to_audit"]},
                f,
                sort_keys=False,
                allow_unicode=True,
                default_flow_style=False,
            )
            f.write("\n\n\n")

            # Write unmapped_source_fields section
            yaml.safe_dump(
                {"unmapped_source_fields": output_data["unmapped_source_fields"]},
                f,
                sort_keys=False,
                allow_unicode=True,
                default_flow_style=False,
            )
            f.write("\n\n\n")

            # Write unmapped_target_fields section
            yaml.safe_dump(
                {"unmapped_target_fields": output_data["unmapped_target_fields"]},
                f,
                sort_keys=False,
                allow_unicode=True,
                default_flow_style=False,
            )

        duration_ms = int((time.time() - start_time) * 1000)

        # JSONL summary logging
        summary_data = {
            "step": "map",
            "object": args.object,
            "variant": args.variant,
            "source_index": str(source_index_file).replace("\\", "/"),
            "target_index": str(target_index_file).replace("\\", "/"),
            "output_file": str(mapping_file).replace("\\", "/"),
            "mapped": mapped_count,
            "unmapped": unmapped_count,
            "to_audit": to_audit_count,
            "unused_sources": unused_sources_count,
            "duration_ms": duration_ms,
            "warnings": [],
        }

        # Add ruleset_sources to metadata if central mapping file exists
        if central_mapping_file.exists():
            output_data["metadata"]["ruleset_sources"] = str(
                central_mapping_file
            ).replace("\\", "/")
            summary_data["ruleset_sources"] = str(central_mapping_file).replace(
                "\\", "/"
            )

        # Prepare preview data for human output (first 12 mappings)
        preview_data = []
        for mapping in mapping_result["mappings"][:12]:
            preview_data.append({
                "target_field": mapping["target_field"],
                "source_header": mapping["source_header"] or "null",
                "source_field_name": mapping.get("source_field_name", "field_name onbekend"),  # Always show field_name
                "confidence": f"{mapping['confidence']:.2f}",
                "status": mapping["status"],
            })

        # Log event using Enhanced Logger (this will handle both stdout and file logging)
        logger.log_event(summary_data, preview_data)

        # Generate HTML report if enabled
        if not getattr(args, 'no_html', False):
            from .reporting import write_html_report
            import json
            from datetime import datetime as dt
            
            timestamp = dt.now().strftime("%Y%m%d_%H%M")
            
            # Determine report directory for F03 (map) reports
            if hasattr(args, 'html_dir') and args.html_dir:
                reports_dir = Path(args.html_dir)
            else:
                reports_dir = root_path / "data" / "05_map"
            
            # Generate enriched summary for HTML report
            html_summary = {
                "step": "map",
                "object": args.object,
                "variant": args.variant,
                "ts": dt.now().isoformat(),
                "source_index": str(source_index_file.relative_to(Path(args.root))),
                "target_index": str(target_index_file.relative_to(Path(args.root))),
                "mapped": mapped_count,
                "unmapped": unmapped_count,
                "to_audit": to_audit_count,
                "unused_sources": unused_sources_count,
                "mappings": [
                    {
                        "target_table": mapping.get("target_table", ""),
                        "target_field": mapping["target_field"],
                        "source_header": mapping["source_header"],
                        "required": mapping.get("required", False),
                        "confidence": mapping["confidence"],
                        "status": mapping["status"],
                        "rationale": mapping["rationale"]
                    }
                    for mapping in mapping_result["mappings"]
                ],
                "to_audit_rows": [
                    {
                        "target_table": audit.get("target_table", ""),
                        "target_field": audit["target_field"],
                        "source_header": audit.get("source_header"),
                        "confidence": audit.get("confidence", 0.0),
                        "reason": audit.get("reason", "")
                    }
                    for audit in mapping_result["to_audit"]
                ],
                "unmapped_source_fields": mapping_result["unmapped_source_fields"],
                "unmapped_target_fields": [
                    {
                        "target_table": target.get("target_table", ""),
                        "target_field": target.get("target_field", str(target)),
                        "required": target.get("required", False)
                    } if isinstance(target, dict) else {"target_field": str(target), "required": False}
                    for target in mapping_result["unmapped_target_fields"]
                ],
                "warnings": []
            }
            
            # Write JSON summary
            json_filename = f"mapping_{timestamp}.json"
            json_path = reports_dir / json_filename
            json_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(html_summary, f, ensure_ascii=False, indent=2)
            
            # Write HTML report
            html_filename = f"mapping_{timestamp}.html"
            html_path = reports_dir / html_filename
            title = f"mapping · {args.object}/{args.variant}"
            
            write_html_report(html_summary, html_path, title)
            
            # Human-readable logging with forward slashes
            html_path_display = str(html_path.relative_to(Path(args.root))).replace('\\', '/')
            if not (args.json or not sys.stdout.isatty()):
                print(f"report: {html_path_display}")

    except Exception as e:
        error_data = {"error": "exception", "message": str(e)}
        logger.log_error(error_data)
        sys.exit(1)


def run_transform_command(args, config):
    """Run the transform command - transforms raw data through ETL pipeline to SAP CSV."""
    from .enhanced_logging import EnhancedLogger
    import csv
    import glob
    import re
    import time
    from datetime import datetime

    start_time = time.time()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")

    # Track warnings for final summary
    warnings = []

    logger.info(f"=== Transform Command: {args.object}/{args.variant} ===")

    # Set up paths using root directory
    root_path = Path(args.root)
    
    # Initialize enhanced logger
    enhanced_logger = EnhancedLogger(args, "transform", args.object, args.variant, root_path)
    
    migrations_dir = root_path / "migrations" / args.object / args.variant

    # Input files (F04 spec: data/07_raw/{object}_{variant}.xlsx)
    raw_file = root_path / "data" / "07_raw" / f"{args.object}_{args.variant}.xlsx"
    mapping_file = migrations_dir / "mapping.yaml"
    target_index_file = migrations_dir / "index_target.yaml"

    # Optional config files
    transformations_file = root_path / "config" / "transformations.yaml"
    value_rules_file = root_path / "config" / "value_rules.yaml"
    validation_file = root_path / "config" / "validation.yaml"
    root_path / "config" / "central_mapping_memory.yaml"

    # Output paths
    output_dir = root_path / "data" / "10_transformed"
    output_dir.mkdir(parents=True, exist_ok=True)

    rejects_dir = root_path / "data" / "09_rejected"
    rejects_dir.mkdir(parents=True, exist_ok=True)

    raw_validation_dir = root_path / "data" / "08_raw_validation"
    raw_validation_dir.mkdir(parents=True, exist_ok=True)

    transformed_validation_dir = root_path / "data" / "11_transformed_validation"
    transformed_validation_dir.mkdir(parents=True, exist_ok=True)

    # Template glob pattern  
    template_glob = str(
        root_path / "data" / "06_template" / f"S_{args.variant.upper()}#*.csv"
    )

    # Primary outputs
    sap_csv = output_dir / f"S_{args.variant.upper()}#{args.object}_Data.csv"
    snapshot_csv = (
        output_dir / f"S_{args.variant.upper()}#{args.object}_{timestamp}_output.csv"
    )
    rejects_csv = rejects_dir / f"rejected_{args.object}_{args.variant}_{timestamp}.csv"

    # Check required files
    if not raw_file.exists():
        error_data = {
            "error": "missing_raw",
            "object": args.object,
            "variant": args.variant,
            "expected_path": str(raw_file),
        }
        enhanced_logger.log_error(error_data)
        sys.exit(2)

    if not mapping_file.exists():
        error_data = {
            "error": "missing_mapping",
            "object": args.object,
            "variant": args.variant,
            "expected_path": str(mapping_file),
        }
        enhanced_logger.log_error(error_data)
        sys.exit(3)

    if not target_index_file.exists():
        error_data = {
            "error": "missing_target_index",
            "object": args.object,
            "variant": args.variant,
            "expected_path": str(target_index_file),
        }
        enhanced_logger.log_error(error_data)
        sys.exit(4)

    # Check overwrite policy (only check snapshot and rejects, no longer checking sap_csv)
    if (snapshot_csv.exists() or rejects_csv.exists()) and not args.force:
        error_data = {
            "error": "would_overwrite",
            "object": args.object,
            "variant": args.variant,
            "existing_files": [str(f) for f in [snapshot_csv, rejects_csv] if f.exists()],
        }
        enhanced_logger.log_error(error_data)
        sys.exit(5)

    try:
        # Load raw data
        logger.info("Loading raw XLSX data...")
        raw_df = pd.read_excel(raw_file, dtype=str)
        # Replace NaN with empty strings and trim
        raw_df = raw_df.fillna("").astype(str)
        for col in raw_df.columns:
            raw_df[col] = raw_df[col].str.strip()

        rows_in = len(raw_df)
        logger.info(f"Loaded {rows_in} rows from raw data")

        # Load mapping configuration
        with open(mapping_file, "r", encoding="utf-8") as f:
            mapping_data = yaml.safe_load(f)

        # Load target index
        with open(target_index_file, "r", encoding="utf-8") as f:
            target_data = yaml.safe_load(f)
        target_fields = target_data.get("target_fields", [])

        # Load optional configurations
        if transformations_file.exists():
            with open(transformations_file, "r", encoding="utf-8") as f:
                yaml.safe_load(f) or {}

        if value_rules_file.exists():
            with open(value_rules_file, "r", encoding="utf-8") as f:
                yaml.safe_load(f) or {}

        validation_config = {}
        if validation_file.exists():
            with open(validation_file, "r", encoding="utf-8") as f:
                validation_config = yaml.safe_load(f) or {}

        # Template processing
        template_path = None
        template_headers = None
        template_matches = glob.glob(template_glob)

        if template_matches:
            template_path = template_matches[0]  # Use first match
            logger.info(f"Using template: {template_path}")

            # Read template headers
            with open(template_path, "r", encoding="utf-8", newline="") as f:
                reader = csv.reader(f)
                template_headers = next(reader)
        else:
            logger.warning(f"Template missing for pattern: {template_glob}")
            warnings.append({"warning": "template_missing"})

        # 2) Raw validation report
        logger.info("Generating raw validation report...")
        raw_validation_file = (
            raw_validation_dir
            / f"raw_validation_{args.object}_{args.variant}_{timestamp}.csv"
        )
        raw_validation_json = (
            raw_validation_dir
            / f"raw_validation_{args.object}_{args.variant}_{timestamp}.json"
        )

        raw_stats = []
        for col in raw_df.columns:
            total = len(raw_df)
            empty_count = int((raw_df[col] == "").sum())
            pct_empty = (empty_count / total * 100) if total > 0 else 0
            raw_stats.append(
                {
                    "source_header": col,
                    "total": int(total),
                    "empty_count": empty_count,
                    "pct_empty": round(float(pct_empty), 2),
                }
            )

        # Add warnings for missing source columns referenced in mapping
        mapping_entries = mapping_data.get("mappings", [])
        for mapping in mapping_entries:
            source_header = mapping.get("source_header")
            if source_header and source_header not in raw_df.columns:
                warnings.append(
                    {"warning": "missing_source_column", "column": source_header}
                )
                raw_stats.append(
                    {
                        "source_header": source_header,
                        "total": len(raw_df),
                        "empty_count": len(raw_df),
                        "pct_empty": 100.0,
                    }
                )

        # Save raw validation
        raw_stats_df = pd.DataFrame(raw_stats)
        raw_stats_df.to_csv(raw_validation_file, index=False)
        with open(raw_validation_json, "w", encoding="utf-8") as f:
            json.dump(raw_stats, f, indent=2)

        # Generate HTML report for RAW validation if enabled
        if not getattr(args, 'no_html', False):
            from .reporting import write_html_report
            from datetime import datetime as dt
            
            timestamp_html = dt.now().strftime("%Y%m%d_%H%M")
            
            # Determine report directory for RAW validation
            if hasattr(args, 'html_dir') and args.html_dir:
                reports_dir = Path(args.html_dir)
            else:
                reports_dir = raw_validation_dir
            
            # Generate enriched summary for RAW validation HTML report
            null_rate_by_source = {stat["source_header"]: stat["pct_empty"] / 100.0 for stat in raw_stats}
            missing_sources = [stat["source_header"] for stat in raw_stats if stat["pct_empty"] == 100.0]
            
            # Add data profiling for RAW validation
            from .reporting import profile_dataframe
            raw_profiles = profile_dataframe(raw_df)
            
            html_summary_raw = {
                "step": "raw_validation",
                "object": args.object,
                "variant": args.variant,
                "ts": dt.now().isoformat(),
                "rows_in": len(raw_df),
                "null_rate_by_source": null_rate_by_source,
                "missing_sources": missing_sources,
                "field_profiles": raw_profiles,
                "warnings": [w for w in warnings if w.get("warning") == "missing_source_column"]
            }
            
            # Write JSON summary for RAW validation
            json_filename_raw = f"raw_validation_{args.object}_{args.variant}_{timestamp_html}.json"
            json_path_raw = reports_dir / json_filename_raw
            json_path_raw.parent.mkdir(parents=True, exist_ok=True)
            
            with open(json_path_raw, 'w', encoding='utf-8') as f:
                json.dump(html_summary_raw, f, ensure_ascii=False, indent=2)
            
            # Write HTML report for RAW validation
            html_filename_raw = f"raw_validation_{args.object}_{args.variant}_{timestamp_html}.html"
            html_path_raw = reports_dir / html_filename_raw
            title_raw = f"raw_validation · {args.object}/{args.variant}"
            
            write_html_report(html_summary_raw, html_path_raw, title_raw)
            
            # Human-readable logging with forward slashes
            html_path_display_raw = str(html_path_raw.relative_to(root_path)).replace('\\', '/')
            if not (args.json or not sys.stdout.isatty()):
                print(f"report: {html_path_display_raw}")

        # 3) Create skeleton DataFrame with target field base names
        logger.info("Creating skeleton with target fields...")
        skeleton_columns = {}
        ignored_targets = []

        for target in target_fields:
            sap_field = target.get("sap_field", "")
            base_name = sap_field.upper() if sap_field else ""
            if base_name:
                skeleton_columns[base_name.lower()] = base_name

        # Initialize skeleton with all target columns (lowercase keys, empty values)
        skeleton = pd.DataFrame(index=raw_df.index)
        for col_lower in skeleton_columns.keys():
            skeleton[col_lower] = ""

        # 4) Fill skeleton from mapping
        logger.info("Filling skeleton from mapping...")
        for mapping in mapping_entries:
            target_field = mapping.get("target_field", "")
            source_header = mapping.get("source_header")

            if target_field and source_header:
                target_base = target_field.upper()
                target_lower = target_base.lower()

                if target_lower in skeleton.columns:
                    if source_header in raw_df.columns:
                        skeleton[target_lower] = raw_df[source_header]
                    else:
                        # Already warned about missing source column
                        skeleton[target_lower] = ""

        # 5) Apply transformations (basic implementation)
        logger.info("Applying transformations...")
        # TODO: Implement full transformation pipeline from transformations.yaml

        # 6) Apply value rules (basic implementation)
        logger.info("Applying value rules...")
        # TODO: Implement value rules from value_rules.yaml

        # 7) Validation and splitting
        logger.info("Validating data and splitting good/bad records...")

        # Build validation rules from validation.yaml (with F02 fallback)
        key_required_config = {}

        # First, get key/required from F02 (index_target.yaml)
        for target in target_fields:
            sap_field = target.get("sap_field", "")
            if sap_field:
                base_name = sap_field.upper()
                key_required_config[base_name] = {
                    "key": bool(target.get("key", False)),
                    "required": bool(target.get("mandatory", False)),
                }

        # Override with validation.yaml if present
        if validation_config:
            for field_name, rules in validation_config.items():
                base_name = field_name.upper()
                if "key" in rules or "required" in rules:
                    if base_name not in key_required_config:
                        key_required_config[base_name] = {}
                    if "key" in rules:
                        key_required_config[base_name]["key"] = bool(rules["key"])
                    if "required" in rules:
                        key_required_config[base_name]["required"] = bool(
                            rules["required"]
                        )

                # Validate key=true implies required=true
                config = key_required_config.get(base_name, {})
                if config.get("key") and not config.get("required"):
                    error_data = {
                        "error": "invalid_validation_config",
                        "field": base_name,
                        "issue": "key=true but required=false",
                    }
                    if args.json or not sys.stdout.isatty():
                        print(json.dumps(error_data))
                    else:
                        logger.error(
                            f"Invalid validation config for {base_name}: key=true but required=false"
                        )
                    sys.exit(6)

        # Apply validation rules
        rejected_rows = []
        error_stats = {}

        for idx, row in skeleton.iterrows():
            row_errors = []

            for col_lower, base_name in skeleton_columns.items():
                value = row[col_lower]
                config = key_required_config.get(base_name, {})

                # Required validation
                if config.get("required", False) and value == "":
                    error_label = f"{base_name}.required"
                    row_errors.append(error_label)
                    error_stats[error_label] = error_stats.get(error_label, 0) + 1

                # TODO: Add other validation rules (regex, max_length, type, etc.)

            if row_errors:
                rejected_rows.append(
                    {
                        "__rownum": idx + 1,
                        "__errors": "|".join(row_errors),
                        "__first_error": row_errors[0],
                        "__timestamp": datetime.now().isoformat(),
                        **{skeleton_columns[col]: row[col] for col in skeleton.columns},
                    }
                )

        # Split into accepted and rejected
        rejected_indices = [r["__rownum"] - 1 for r in rejected_rows]
        accepted_skeleton = (
            skeleton.drop(index=rejected_indices)
            if rejected_indices
            else skeleton.copy()
        )

        rows_out = len(accepted_skeleton)
        rows_rejected = len(rejected_rows)

        # 8) Template processing and column annotation
        logger.info("Processing template and applying annotations...")

        # Parse template headers to get base names and order
        template_map = {}  # base_name -> annotated_header
        final_column_order = []

        if template_headers:
            for header in template_headers:
                # Strip annotation to get base name
                base_match = re.match(r"^([^()]+)", header.strip())
                if base_match:
                    base_name = base_match.group(1).upper()
                    template_map[base_name] = header
                    final_column_order.append(base_name)
        else:
            # Fallback: use F02 order
            for target in target_fields:
                sap_field = target.get("sap_field", "")
                if sap_field:
                    base_name = sap_field.upper()
                    final_column_order.append(base_name)

        # Check template vs targets reconciliation
        for base_name in skeleton_columns.values():
            if base_name not in template_map and template_headers:
                warnings.append(
                    {"warning": "target_not_in_template", "field": base_name}
                )
                ignored_targets.append(base_name)

        # Apply correct annotation based on validation config
        final_headers = []
        final_data = pd.DataFrame()

        for base_name in final_column_order:
            if base_name in ignored_targets:
                continue  # Skip fields not in template

            config = key_required_config.get(base_name, {})
            key = config.get("key", False)
            required = config.get("required", False)

            # Annotation rules
            if key and required:
                annotated_header = f"{base_name}(k/*)"
            elif required:
                annotated_header = f"{base_name}(*)"
            else:
                annotated_header = base_name

            final_headers.append(annotated_header)

            # Get data from skeleton
            col_lower = base_name.lower()
            if col_lower in accepted_skeleton.columns:
                final_data[annotated_header] = accepted_skeleton[col_lower]
            else:
                final_data[annotated_header] = ""

        # 9) Write Snapshot CSV only (removing SAP CSV generation as per requirement 4)
        logger.info("Writing snapshot CSV...")

        def write_sap_csv(df, filepath):
            """Write CSV with SAP requirements: UTF-8, CRLF, proper quoting"""
            with open(filepath, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(
                    f,
                    delimiter=",",
                    quotechar='"',
                    lineterminator="\r\n",
                    quoting=csv.QUOTE_MINIMAL,
                )
                # Write headers
                writer.writerow(final_headers)
                # Write data
                for _, row in df.iterrows():
                    writer.writerow([row[col] for col in final_headers])

        # Write only snapshot CSV (timestamped format: S_{variant}#{object}_{timestamp}_output.csv)
        # This format is accepted by SAP Migrate Your Data as long as S_ prefix and # separator are used
        write_sap_csv(final_data, snapshot_csv)

        # Write rejected records
        if rejected_rows:
            rejected_df = pd.DataFrame(rejected_rows)
            rejected_df.to_csv(rejects_csv, index=False)
            
            # Generate HTML report for rejected records
            try:
                from .csv_reporting import generate_csv_html_report
                
                rejects_html = rejects_csv.with_suffix('.html')
                report_title = f"Rejected Records Report · {args.object}/{args.variant}"
                
                generate_csv_html_report(rejects_csv, rejects_html, report_title)
                logger.info(f"Generated HTML rejects report: {rejects_html}")
                
            except Exception as e:
                logger.warning(f"Failed to generate HTML rejects report: {e}")
                # Don't fail the entire transform if HTML generation fails

        # 10) Post-transform validation report
        (
            transformed_validation_dir
            / f"post_transform_validation_{args.object}_{args.variant}_{timestamp}.csv"
        )
        post_transform_json = (
            transformed_validation_dir
            / f"post_transform_validation_{args.object}_{args.variant}_{timestamp}.json"
        )

        post_stats = {
            "rows_in": rows_in,
            "rows_out": rows_out,
            "rows_rejected": rows_rejected,
            "errors_by_rule": error_stats,
            "errors_by_field": {},
        }

        # Group errors by field
        for error_label in error_stats:
            field_name = error_label.split(".")[0]
            post_stats["errors_by_field"][field_name] = (
                post_stats["errors_by_field"].get(field_name, 0)
                + error_stats[error_label]
            )

        with open(post_transform_json, "w", encoding="utf-8") as f:
            json.dump(post_stats, f, indent=2)

        # Generate HTML report for POST-transform validation if enabled
        if not getattr(args, 'no_html', False):
            from .reporting import write_html_report
            from datetime import datetime as dt
            
            timestamp_html = dt.now().strftime("%Y%m%d_%H%M")
            
            # Determine report directory for POST validation
            if hasattr(args, 'html_dir') and args.html_dir:
                reports_dir = Path(args.html_dir)
            else:
                reports_dir = transformed_validation_dir
            
            # Calculate mapped coverage
            total_mapped_fields = len([m for m in mapping_entries if m.get("source_header")])
            total_target_fields = len(target_fields)
            mapped_coverage = total_mapped_fields / total_target_fields if total_target_fields > 0 else 0.0
            
            # Generate sample rows with errors
            sample_rows = []
            if len(final_data) > 0:
                error_sample = final_data.head(200)  # Take first 200 rows
                for idx, row in error_sample.iterrows():
                    row_dict = {"__rownum": idx + 1}
                    # Add top 3 target fields as sample
                    target_sample = list(final_data.columns)[:3]
                    for col in target_sample:
                        row_dict[col] = str(row[col]) if pd.notna(row[col]) else ""
                    
                    # Add errors (simplified - could be enhanced with actual validation)
                    row_errors = []
                    for col in target_sample:
                        if pd.isna(row[col]) or str(row[col]).strip() == "":
                            row_errors.append(f"{col}.required")
                    row_dict["errors"] = row_errors
                    sample_rows.append(row_dict)
            
            # Add data profiling for POST-transform validation (on skeleton before split)
            from .reporting import profile_dataframe
            
            # Prepare validation rules mapping for profiler
            validation_rules_mapping = {}
            if validation_config:
                for field_name, rules in validation_config.items():
                    validation_rules_mapping[field_name.lower()] = rules
            
            # Profile the skeleton (transformed target columns before splitting)
            post_profiles = profile_dataframe(skeleton, validation_rules_mapping)
            
            # Generate enriched summary for POST-transform validation HTML report
            html_summary_post = {
                "step": "post_transform_validation",
                "object": args.object,
                "variant": args.variant,
                "structure": f"S_{args.variant.upper()}",
                "ts": dt.now().isoformat(),
                "rows_in": rows_in,
                "rows_out": rows_out,
                "rows_rejected": rows_rejected,
                "mapped_coverage": mapped_coverage,
                "template_used": template_path or f"data/06_template/S_{args.variant.upper()}#*.csv",
                "ignored_targets": ignored_targets,
                "errors_by_rule": error_stats,
                "errors_by_field": post_stats["errors_by_field"],
                "sample_rows": sample_rows,
                "field_profiles": post_profiles,
                "warnings": warnings
            }
            
            # Write JSON summary for POST validation
            json_filename_post = f"post_transform_validation_{args.object}_{args.variant}_{timestamp_html}.json"
            json_path_post = reports_dir / json_filename_post
            json_path_post.parent.mkdir(parents=True, exist_ok=True)
            
            with open(json_path_post, 'w', encoding='utf-8') as f:
                json.dump(html_summary_post, f, ensure_ascii=False, indent=2)
            
            # Write HTML report for POST validation
            html_filename_post = f"post_transform_validation_{args.object}_{args.variant}_{timestamp_html}.html"
            html_path_post = reports_dir / html_filename_post
            title_post = f"post_transform_validation · S_{args.variant.upper()} · {args.object}/{args.variant}"
            
            write_html_report(html_summary_post, html_path_post, title_post)
            
            # Human-readable logging with forward slashes
            html_path_display_post = str(html_path_post.relative_to(root_path)).replace('\\', '/')
            if not (args.json or not sys.stdout.isatty()):
                print(f"report: {html_path_display_post}")

        # Calculate final metrics
        duration_ms = int((time.time() - start_time) * 1000)

        # Summary logging (no longer including sap_csv)
        summary = {
            "step": "transform",
            "object": args.object,
            "variant": args.variant,
            "input_raw": str(raw_file),
            "mapping": str(mapping_file),
            "target_index": str(target_index_file),
            "template_glob": template_glob,
            "template_used": template_path,
            "snapshot_csv": str(snapshot_csv),
            "rejects_csv": str(rejects_csv) if rejected_rows else None,
            "ignored_targets": ignored_targets,
            "rows_in": rows_in,
            "rows_out": rows_out,
            "rows_rejected": rows_rejected,
            "duration_ms": duration_ms,
            "warnings": warnings,
        }

        # Prepare preview data for enhanced logger (first 8 columns, 5 rows)
        preview_data = []
        if len(final_data) > 0:
            preview_cols = final_headers[:8]
            preview_df = final_data[preview_cols].head(5)
            
            for idx, row in preview_df.iterrows():
                row_dict = {}
                for col in preview_cols:
                    row_dict[col] = str(row[col])[:15] if pd.notna(row[col]) else ""
                preview_data.append(row_dict)

        # Log event using Enhanced Logger (this will handle both stdout and file logging)
        enhanced_logger.log_event(summary, preview_data)

        logger.info("✓ Transform command completed successfully!")

    except Exception as e:
        error_data = {"error": "exception", "message": str(e)}
        enhanced_logger.log_error(error_data)
        sys.exit(1)


def main():
    """Main entry point for the application."""
    from .logging_config import setup_logging

    # Initialize logging
    setup_logging()

    args, config, is_legacy = setup_cli()

    # Execute the appropriate command
    if args.command == "index_source":
        run_index_source_command(args, config)
    elif args.command == "index_target":
        run_index_target_command(args, config)
    elif args.command == "map":
        run_map_command(args, config)
    elif args.command == "transform":
        run_transform_command(args, config)
    else:
        logger.error(f"Unknown command: {args.command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
