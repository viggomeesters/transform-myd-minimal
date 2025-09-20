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
    # Look in configs directory first, fallback to root for backward compatibility
    central_memory_path = base_path / "configs" / "central_mapping_memory.yaml"
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

        return CentralMappingMemory(
            global_skip_fields=global_skip_fields,
            global_manual_mappings=global_manual_mappings,
            table_specific=table_specific,
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
            # Read just a few rows to check if sheet has data
            df = pd.read_excel(file_path, sheet_name=sheet_name, nrows=10)
            if not df.empty and not df.dropna(how="all").empty:
                return sheet_name
        raise ValueError("No non-empty worksheets found")
    except Exception as e:
        raise ValueError(f"Error reading Excel file: {e}")


def find_header_row(file_path: Path, sheet_name: str) -> Tuple[int, List[str]]:
    """Find the first row with ≥1 non-empty cell and return headers."""
    try:
        # Read the entire sheet to find header row
        df_full = pd.read_excel(file_path, sheet_name=sheet_name, header=None)

        for row_idx in range(len(df_full)):
            row_data = df_full.iloc[row_idx]
            # Check if row has at least one non-empty cell
            non_empty_cells = row_data.dropna()
            if len(non_empty_cells) >= 1:
                # This is our header row
                headers = []
                for cell in row_data:
                    if pd.isna(cell):
                        headers.append("")
                    else:
                        # Trim surrounding whitespace
                        headers.append(str(cell).strip())
                return row_idx, headers

        raise ValueError("No header row found with ≥1 non-empty cell")
    except Exception as e:
        raise ValueError(f"Error finding header row: {e}")


def analyze_column_data(
    file_path: Path, sheet_name: str, header_row: int, headers: List[str]
) -> List[Dict]:
    """Analyze column data to infer types, nullable status, and examples."""
    try:
        # Read the full sheet to get access to all columns
        df_full = pd.read_excel(file_path, sheet_name=sheet_name, header=None)

        # Get data rows (everything after header row)
        data_rows = (
            df_full.iloc[header_row + 1 :]
            if header_row + 1 < len(df_full)
            else pd.DataFrame()
        )

        field_data = []
        col_idx = 0

        for header in headers:
            if header.strip():  # Only process non-empty headers
                # Find the column index for this header in the original data
                if col_idx < len(data_rows.columns):
                    column_data = data_rows.iloc[:, col_idx]

                    # Check for nulls
                    has_nulls = column_data.isna().any()

                    # Get non-null values for type inference
                    non_null_values = column_data.dropna()

                    # Infer data type
                    if len(non_null_values) > 0:
                        dtype = infer_dtype(non_null_values, skipna=True)
                        # Get first non-null value as example
                        example = (
                            str(non_null_values.iloc[0])
                            if len(non_null_values) > 0
                            else ""
                        )
                    else:
                        dtype = "empty"
                        example = ""

                    field_data.append(
                        OrderedDict(
                            [
                                ("field_name", header),
                                ("field_description", None),
                                ("example", example),
                                ("dtype", dtype),
                                ("nullable", bool(has_nulls)),
                            ]
                        )
                    )
                else:
                    # Column index beyond available data
                    field_data.append(
                        OrderedDict(
                            [
                                ("field_name", header),
                                ("field_description", None),
                                ("example", ""),
                                ("dtype", "empty"),
                                ("nullable", True),
                            ]
                        )
                    )

            col_idx += 1

        return field_data
    except Exception as e:
        raise ValueError(f"Error analyzing column data: {e}")



def run_index_source_command(args):
    """Run the index_source command - parse headers from XLSX and create index_source.yaml."""
    from .enhanced_logging import EnhancedLogger
    
    warnings = []
    root_path = Path(args.root) if hasattr(args, "root") else Path(".")
    
    # Initialize enhanced logger
    logger = EnhancedLogger(args, "index_source", args.object, args.variant, root_path)

    try:
        # Construct input file path
        input_file = (
            root_path
            / "data"
            / "01_source"
            / f"index_source_{args.object}_{args.variant}.xlsx"
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

        # Filter out empty headers and warn about them
        processed_headers = []
        for i, header in enumerate(headers):
            if header.strip():
                processed_headers.append(header)
            elif header == "":
                warnings.append(f"Empty header found at column {i+1}")

        if not processed_headers:
            error_data = {"error": "no_headers"}
            logger.log_error(error_data)
            sys.exit(3)

        # Analyze column data
        try:
            source_fields = analyze_column_data(
                input_file, sheet_name, header_row_idx, processed_headers
            )
        except ValueError as e:
            error_data = {"error": "exception", "message": str(e)}
            logger.log_error(error_data)
            sys.exit(1)

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
            source_data = {
                "metadata": {
                    "object": args.object,
                    "variant": args.variant,
                    "source_file": f"data/01_source/index_source_{args.object}_{args.variant}.xlsx",
                    "generated_at": datetime.now().isoformat(),
                    "sheet": sheet_name,
                    "source_fields_count": len(source_fields),
                },
                "source_fields": source_fields,
            }

            # Write index_source.yaml
            with open(output_file, "w", encoding="utf-8") as f:
                yaml.dump(source_data, f, default_flow_style=False, allow_unicode=True)

        # Update global object list
        update_object_list(args.object, args.variant, root_path)

        # Prepare preview data for human output (first 8 headers)
        preview_data = []
        for i, field in enumerate(source_fields[:8]):
            preview_data.append({
                "field_name": field.get("field_name", ""),
                "dtype": field.get("dtype", ""),
                "nullable": field.get("nullable", True),
                "example": field.get("example", "")
            })

        # Log summary
        summary_data = {
            "step": "index_source",
            "object": args.object,
            "variant": args.variant,
            "input_file": str(input_file),
            "output_file": str(output_file),
            "total_columns": len(source_fields),
            "warnings": warnings,
        }
        logger.log_event(summary_data, preview_data)

    except Exception as e:
        error_data = {"error": "exception", "message": str(e)}
        logger.log_error(error_data)
        sys.exit(1)


def _parse_spreadsheetml_target_fields(xml_path: Path, variant: str) -> List[Dict[str, Any]]:
    """
    Parse SpreadsheetML XML file according to F02 specification.
    
    Returns list of target field dictionaries with exact key ordering:
    ["sap_field","field_description","sap_table","mandatory","field_group","key","sheet_name","data_type","length","decimal"]
    """
    import xml.etree.ElementTree as ET
    
    # Parse XML
    tree = ET.parse(xml_path)
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
    structure_pattern = f"S_{variant.upper()}"
    
    for row_data in parsed_rows[header_row_idx + 1:]:
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
        field_group_raw = row_data[2] if len(row_data) > 2 else None  # Column 3 -> index 2
        field_description = row_data[3] if len(row_data) > 3 else None  # Column 4 -> index 3
        importance_raw = row_data[4] if len(row_data) > 4 else None  # Column 5 -> index 4
        data_type = row_data[5] if len(row_data) > 5 else None  # Column 6 -> index 5
        length_raw = row_data[6] if len(row_data) > 6 else None  # Column 7 -> index 6
        decimal_raw = row_data[7] if len(row_data) > 7 else None  # Column 8 -> index 7
        sap_table_raw = row_data[8] if len(row_data) > 8 else None  # Column 9 -> index 8
        sap_field_raw = row_data[9] if len(row_data) > 9 else None  # Column 10 -> index 9
        
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
        key = (field_group == "key")
        
        # mandatory: true if contains "mandatory" or in {"X","x","true","1"}
        mandatory = False
        if importance_raw:
            importance_str = str(importance_raw).lower()
            mandatory = ("mandatory" in importance_str or 
                        importance_str in {"x", "true", "1"})
        
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
        
        target_fields.append(row_dict)
    
    return target_fields


def run_index_target_command(args):
    """Run the index_target command - parse XML and filter target fields by variant."""
    from .enhanced_logging import EnhancedLogger
    import xml.etree.ElementTree as ET
    from datetime import datetime
    from pathlib import Path
    
    root_path = Path(args.root).resolve()
    
    # Initialize enhanced logger
    logger = EnhancedLogger(args, "index_target", args.object, args.variant, root_path)
    
    # Construct input file path - check both .xml and fallback formats
    input_file = root_path / f"data/02_target/index_target_{args.object}_{args.variant}.xml"
    
    # Check for fallback files if XML doesn't exist
    if not input_file.exists():
        json_file = root_path / f"data/02_target/index_target_{args.object}_{args.variant}.json"
        yaml_file = root_path / f"data/02_target/index_target_{args.object}_{args.variant}.yaml"
        
        if json_file.exists():
            input_file = json_file
        elif yaml_file.exists():
            input_file = yaml_file
        else:
            error_data = {"error": "missing_input", "path": str(input_file)}
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
        if input_file.suffix == '.xml':
            target_fields = _parse_spreadsheetml_target_fields(input_file, args.variant)
        else:
            # Handle JSON/YAML fallback (simplified for now)
            error_data = {"error": "unsupported_format", "path": str(input_file)}
            logger.log_error(error_data)
            sys.exit(1)
        
        if not target_fields:
            error_data = {"error": "no_fields", "structure": f"S_{args.variant.upper()}"}
            logger.log_error(error_data)
            sys.exit(4)
        
        # Create output YAML structure with exact metadata schema
        target_data = {
            "metadata": {
                "object": args.object,
                "variant": args.variant,
                "target_file": f"data/02_target/index_target_{args.object}_{args.variant}.xml",
                "generated_at": datetime.now().isoformat(),
                "structure": f"S_{args.variant.upper()}"
            },
            "target_fields": target_fields
        }
        
        # Write YAML with preserved order (using yaml.safe_dump as specified)
        with open(output_file, "w", encoding="utf-8") as f:
            yaml.safe_dump(target_data, f, sort_keys=False, allow_unicode=True, default_flow_style=False)
        
        # Prepare preview data for human output (first 8 fields)
        preview_data = []
        for field in target_fields[:8]:
            preview_data.append({
                "sap_field": field.get("sap_field", ""),
                "field_description": field.get("field_description", ""),
                "mandatory": field.get("mandatory", False),
                "data_type": field.get("data_type", ""),
                "length": field.get("length", ""),
                "decimal": field.get("decimal", ""),
                "field_group": field.get("field_group", ""),
                "key": field.get("key", False)
            })
        
        # Log summary
        summary_data = {
            "step": "index_target",
            "object": args.object,
            "variant": args.variant,
            "input_file": str(input_file),
            "output_file": str(output_file),
            "structure": f"S_{args.variant.upper()}",
            "total_fields": len(target_fields),
            "warnings": []
        }
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


def run_map_command(args, config):
    """Run the map command - generates mapping from indexed source and target YAML files."""
    logger.info(f"=== Map Command: {args.object}/{args.variant} ===")

    # Check for indexed source and target files
    migrations_dir = Path(f"migrations/{args.object}/{args.variant}")
    source_index_file = migrations_dir / "index_source.yaml"
    target_index_file = migrations_dir / "index_target.yaml"

    if not source_index_file.exists():
        logger.error(f"Source index file not found: {source_index_file}")
        logger.info(
            f"Please run: ./transform-myd-minimal index_source --object {args.object} --variant {args.variant}"
        )
        sys.exit(1)

    if not target_index_file.exists():
        logger.error(f"Target index file not found: {target_index_file}")
        logger.info(
            f"Please run: ./transform-myd-minimal index_target --object {args.object} --variant {args.variant}"
        )
        sys.exit(1)

    logger.info(f"Reading source index from: {source_index_file}")
    logger.info(f"Reading target index from: {target_index_file}")

    try:
        # Load source fields from index_source.yaml
        with open(source_index_file, "r", encoding="utf-8") as f:
            source_data = yaml.safe_load(f)

        # Load target fields from index_target.yaml
        with open(target_index_file, "r", encoding="utf-8") as f:
            target_data = yaml.safe_load(f)

        # Convert to DataFrames for compatibility with existing matching logic
        source_fields_list = []
        for field in source_data.get("source_fields", []):
            source_fields_list.append(
                {
                    "field_name": field.get("field_name", ""),
                    "field_description": field.get("field_description", ""),
                }
            )

        target_fields_list = []
        for field in target_data.get("target_fields", []):
            target_fields_list.append(
                {
                    "field_name": field.get(
                        "sap_field", ""
                    ),  # Map to sap_field instead of transformer_id
                    "field_description": field.get("description", ""),
                    "field_is_key": False,  # Default values for compatibility
                    "field_is_mandatory": False,
                }
            )

        # Convert to DataFrames
        source_fields = pd.DataFrame(source_fields_list)
        target_fields = pd.DataFrame(target_fields_list)

        logger.info(
            f"Found {len(source_fields)} source fields and {len(target_fields)} target fields"
        )

        # Load central mapping memory
        base_dir = Path.cwd()
        logger.info("Loading central mapping memory...")
        central_memory = load_central_mapping_memory(base_dir)
        if central_memory:
            logger.info("Central mapping memory loaded successfully")
            skip_rules, manual_mappings = get_effective_rules_for_table(
                central_memory, args.object, args.variant
            )
            logger.info(
                f"Found {len(skip_rules)} skip rules and {len(manual_mappings)} manual mappings for {args.object}_{args.variant}"
            )
        else:
            logger.info("No central mapping memory found or failed to load")

        # Configure fuzzy matching using config values
        fuzzy_config = FuzzyConfig(
            enabled=not config.disable_fuzzy,
            threshold=config.fuzzy_threshold,
            max_suggestions=config.max_suggestions,
        )

        # Create advanced mapping with central memory support
        mapping_result = create_advanced_column_mapping(
            source_fields,
            target_fields,
            fuzzy_config,
            central_memory,
            args.object,
            args.variant,
        )
        (
            mapping_lines,
            exact_matches,
            fuzzy_matches,
            unmapped_sources,
            audit_matches,
            central_skip_matches,
            central_manual_matches,
        ) = mapping_result

        # Print matching statistics
        logger.info("")
        logger.info("=== Advanced Matching Results ===")
        if central_skip_matches:
            logger.info(
                f"Central memory skip rules applied: {len(central_skip_matches)}"
            )
        if central_manual_matches:
            logger.info(
                f"Central memory manual mappings applied: {len(central_manual_matches)}"
            )
        logger.info(f"Exact matches: {len(exact_matches)}")
        logger.info(f"Fuzzy/Synonym matches: {len(fuzzy_matches)}")
        logger.info(f"Unmapped sources: {len(unmapped_sources)}")
        logger.info(
            f"Audit matches (fuzzy to exact-mapped targets): {len(audit_matches)}"
        )
        logger.info(
            f"Mapping coverage: {((len(exact_matches) + len(fuzzy_matches)) / len(source_fields) * 100):.1f}%"
        )

        # Show detailed results
        if central_skip_matches:
            logger.info("")
            logger.info("Central memory skip rules applied:")
            for match in central_skip_matches:
                logger.info(f"  SKIP: {match.source_field} - {match.reason}")

        if central_manual_matches:
            logger.info("")
            logger.info("Central memory manual mappings applied:")
            for match in central_manual_matches:
                logger.info(
                    f"  MANUAL: {match.source_field} → {match.target_field} - {match.reason}"
                )

        if fuzzy_matches:
            logger.info("")
            logger.info("Fuzzy/Synonym matches found:")
            for match in fuzzy_matches:
                logger.info(
                    f"  {match.source_field} → {match.target_field} ({match.match_type}, confidence: {match.confidence_score:.2f})"
                )

        if audit_matches:
            logger.info("")
            logger.info("Audit matches found (fuzzy matches to exact-mapped targets):")
            for match in audit_matches:
                logger.info(
                    f"  {match.source_field} → {match.target_field} (audit, confidence: {match.confidence_score:.2f})"
                )

        # Generate mapping.yaml
        mapping_data = {
            "metadata": {
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "object": args.object,
                "variant": args.variant,
                "source_index": str(source_index_file),
                "target_index": str(target_index_file),
                "total_mappings": len(exact_matches)
                + len(fuzzy_matches)
                + len(central_manual_matches),
                "coverage_percentage": (
                    (
                        (
                            len(exact_matches)
                            + len(fuzzy_matches)
                            + len(central_manual_matches)
                        )
                        / len(source_fields)
                        * 100
                    )
                    if source_fields.shape[0] > 0
                    else 0
                ),
                "generator": "transform-myd-minimal map",
            },
            "mappings": [],
            "unmapped_sources": [],
            "audit_matches": [],
        }

        # Add all mappings
        all_matches = central_manual_matches + exact_matches + fuzzy_matches
        for match in all_matches:
            if match.target_field:
                mapping_entry = {
                    "source_field": match.source_field,
                    "target_field": match.target_field,
                    "confidence_score": match.confidence_score,
                    "match_type": match.match_type,
                    "reason": match.reason,
                    "source_description": match.source_description,
                    "target_description": match.target_description,
                }
                if match.algorithm:
                    mapping_entry["algorithm"] = match.algorithm
                mapping_data["mappings"].append(mapping_entry)

        # Add unmapped sources
        for unmapped in unmapped_sources:
            mapping_data["unmapped_sources"].append(
                {
                    "source_field": unmapped.source_field,
                    "reason": unmapped.reason,
                    "source_description": unmapped.source_description,
                }
            )

        # Add audit matches
        for audit in audit_matches:
            mapping_data["audit_matches"].append(
                {
                    "source_field": audit.source_field,
                    "target_field": audit.target_field,
                    "confidence_score": audit.confidence_score,
                    "reason": audit.reason,
                    "algorithm": audit.algorithm,
                }
            )

        # Write mapping.yaml
        output_file = migrations_dir / "mapping.yaml"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(
                "# Source-to-target field mappings generated by transform-myd-minimal\n"
            )
            f.write(f"# Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(
                f"# Coverage: {mapping_data['metadata']['coverage_percentage']:.1f}%\n\n"
            )
            yaml.dump(mapping_data, f, default_flow_style=False, allow_unicode=True)

        logger.info(f"Generated mapping.yaml: {output_file}")
        logger.info("✓ Map command completed successfully!")

    except Exception as e:
        logger.error(f"Error creating mapping: {e}")
        sys.exit(1)


def main():
    """Main entry point for the application."""
    from .logging_config import setup_logging

    # Initialize logging
    setup_logging()

    args, config, is_legacy = setup_cli()

    # Execute the appropriate command
    if args.command == "index_source":
        run_index_source_command(args)
    elif args.command == "index_target":
        run_index_target_command(args)
    elif args.command == "map":
        run_map_command(args, config)
    else:
        logger.error(f"Unknown command: {args.command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
