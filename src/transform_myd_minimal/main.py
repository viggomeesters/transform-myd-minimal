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
            # Read with no header row and as text to properly detect headers
            df = pd.read_excel(file_path, sheet_name=sheet_name, header=None, dtype=str, engine="openpyxl")
            if not df.empty:
                # Check if any row has non-empty content
                def is_nonempty_row(r):
                    return any((str(x).strip() != "") for x in r.tolist() if x is not None)
                
                if any(is_nonempty_row(row) for _, row in df.iterrows()):
                    return sheet_name
        raise ValueError("No non-empty worksheets found")
    except Exception as e:
        raise ValueError(f"Error reading Excel file: {e}")


def find_header_row(file_path: Path, sheet_name: str) -> Tuple[int, List[str]]:
    """Find the first row with ≥1 non-empty cell and return headers."""
    try:
        # Read Excel with no header row and as text
        df = pd.read_excel(file_path, sheet_name=sheet_name, header=None, dtype=str, engine="openpyxl")
        
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
        df = pd.read_excel(file_path, sheet_name=sheet_name, header=None, dtype=str, engine="openpyxl")
        
        # Data rows may be zero
        data = df.iloc[header_row + 1:].reset_index(drop=True)
        
        # Build source_fields even when data is empty
        source_fields = []
        for col_i, name in enumerate(headers, start=0):
            if name == "": 
                continue  # Skip empty headers
            
            col = data[col_i] if col_i in data.columns else pd.Series([], dtype="object")
            col = col.astype(str).map(lambda s: s.strip()).replace({"": pd.NA})
            example = (col.dropna().head(1).tolist() or [None])[0]
            
            if example is None:
                dtype_val = "string"
                nullable = True    # unknown → assume nullable
            else:
                dtype_val = infer_dtype([example])
                nullable = col.isna().any()
            
            source_fields.append({
                "field_name": name,
                "field_description": None,
                "example": example,
                "dtype": dtype_val,
                "nullable": bool(nullable),
            })
        
        return source_fields
    except Exception as e:
        raise ValueError(f"Error analyzing column data: {e}")



def run_index_source_command(args, config):
    """Run the index_source command - parse headers from XLSX and create index_source.yaml."""
    from .enhanced_logging import EnhancedLogger
    
    warnings = []
    root_path = Path(args.root) if hasattr(args, "root") else Path(".")
    
    # Initialize enhanced logger
    logger = EnhancedLogger(args, "index_source", args.object, args.variant, root_path)

    try:
        # Use configured input path
        input_file = config.get_input_path(args.object, args.variant)

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
                    "source_file": str(input_file.relative_to(root_path)),
                    "generated_at": datetime.now().isoformat(),
                    "sheet": sheet_name,
                    "source_fields_count": len(source_fields),
                },
                "source_fields": source_fields,
            }

            # Write index_source.yaml
            with open(output_file, "w", encoding="utf-8") as f:
                yaml.safe_dump(source_data, f, sort_keys=False, allow_unicode=True, default_flow_style=False)

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


def run_index_target_command(args, config):
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
            error_data = {"error": "structure_not_found", "variant": args.variant}
            logger.log_error(error_data)
            sys.exit(3)
        
        # Create output YAML structure with exact metadata schema
        target_data = {
            "metadata": {
                "object": args.object,
                "variant": args.variant,
                "target_file": f"data/02_target/index_target_{args.object}_{args.variant}.xml",
                "generated_at": datetime.now().isoformat(),
                "structure": f"S_{args.variant.upper()}",
                "target_fields_count": len(target_fields)
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
        current_lcs = longest_common_substring(current_best.lower(), target_name.lower())
        
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
        spaces = re.sub(r'[^a-zA-Z0-9]', ' ', lowered)
        collapsed = re.sub(r'\s+', ' ', spaces)
        return collapsed.strip()
    
    # Extract verbatim and normalized headers
    verbatim_headers = [field.get("field_name", "") for field in source_fields]
    norm_headers = [norm(header) for header in verbatim_headers]
    
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
                best_rationale = "exact"
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
                        best_rationale = "synonym"
                        break
        
        # 3. FUZZY MATCH: against t_name and t_desc
        if not best_match:
            for i, header in enumerate(verbatim_headers):
                norm_header = normalizer.normalize_field_name(header)
                
                # Try against target field name
                name_score = 0.0
                if t_name:
                    norm_target_name = normalizer.normalize_field_name(t_name)
                    lev_sim = fuzzy_matcher.levenshtein_similarity(norm_header, norm_target_name)
                    jw_sim = fuzzy_matcher.jaro_winkler_similarity(norm_header, norm_target_name) 
                    name_score = max(lev_sim, jw_sim)
                
                # Try against target description
                desc_score = 0.0
                if t_desc:
                    norm_target_desc = normalizer.normalize_field_name(t_desc)
                    lev_sim = fuzzy_matcher.levenshtein_similarity(norm_header, norm_target_desc)
                    jw_sim = fuzzy_matcher.jaro_winkler_similarity(norm_header, norm_target_desc)
                    desc_score = max(lev_sim, jw_sim)
                
                # Take the maximum score from name and description matching
                score = max(name_score, desc_score)
                
                # Apply thresholds per spec
                if score >= 0.85:
                    if score > best_confidence or (score == best_confidence and is_better_match(header, best_match, t_name)):
                        best_match = header
                        best_confidence = score
                        best_rationale = f"fuzzy:{score:.2f}"
                    candidates.append((header, score))
                elif 0.80 <= score < 0.85 and required:
                    # Only map if target is mandatory
                    if score > best_confidence or (score == best_confidence and is_better_match(header, best_match, t_name)):
                        best_match = header
                        best_confidence = score
                        best_rationale = f"fuzzy:{score:.2f}"
                    candidates.append((header, score))
        
        # Handle tiebreakers (tie when delta score <= 0.02)
        candidates.sort(key=lambda x: x[1], reverse=True)
        if len(candidates) > 1 and abs(candidates[0][1] - candidates[1][1]) <= 0.02:
            # Tie detected - add to audit
            to_audit.append({
                "target_table": t_table,
                "target_field": t_name,
                "source_header": best_match,
                "confidence": best_confidence,
                "reason": "tie_break"
            })
        
        # Create mapping entry
        status = "auto" if best_match else "unmapped"
        mapping = {
            "target_table": t_table,
            "target_field": t_name,
            "source_header": best_match,
            "required": required,
            "transforms": [],
            "confidence": round(best_confidence, 2),
            "status": status,
            "rationale": best_rationale
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
            # Low confidence fuzzy
            if 0.80 <= best_confidence < 0.90:
                to_audit.append({
                    "target_table": t_table,
                    "target_field": t_name,
                    "source_header": best_match,
                    "confidence": best_confidence,
                    "reason": "low_confidence_fuzzy"
                })
            
            # Synonym based
            if best_rationale == "synonym":
                to_audit.append({
                    "target_table": t_table,
                    "target_field": t_name,
                    "source_header": best_match,
                    "confidence": best_confidence,
                    "reason": "synonym_based"
                })
        else:
            # Required unmapped
            if required:
                to_audit.append({
                    "target_table": t_table,
                    "target_field": t_name,
                    "source_header": None,
                    "confidence": 0.00,
                    "reason": "required_unmapped"
                })
            
            # Add to unmapped targets
            unmapped_target_fields.append({
                "target_table": t_table,
                "target_field": t_name,
                "required": required
            })
    
    # Handle reused sources audit
    for source_header, mappings_list in reused_sources.items():
        for mapping in mappings_list:
            to_audit.append({
                "target_table": mapping["target_table"],
                "target_field": mapping["target_field"],
                "source_header": source_header,
                "confidence": mapping["confidence"],
                "reason": "reused_source"
            })
    
    # Find unmapped source fields
    unmapped_source_fields = [header for header in verbatim_headers if header not in used_sources]
    
    # Create metadata
    metadata = {
        "object": object_name,
        "variant": variant,
        "generated_at": datetime.now().isoformat(),
        "source_index": f"migrations/{object_name}/{variant}/index_source.yaml",
        "target_index": f"migrations/{object_name}/{variant}/index_target.yaml"
    }
    
    return {
        "metadata": metadata,
        "mappings": mappings,
        "to_audit": to_audit,
        "unmapped_source_fields": unmapped_source_fields,
        "unmapped_target_fields": unmapped_target_fields
    }


def run_map_command(args, config):
    """Run the map command - generates mapping from indexed source and target YAML files."""
    import json
    import time
    from collections import OrderedDict
    
    start_time = time.time()
    logger.info(f"=== Map Command: {args.object}/{args.variant} ===")

    # Set up paths using root directory
    root_path = Path(args.root)
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
            "error": "missing_index_source",
            "object": args.object,
            "variant": args.variant,
            "expected_path": str(source_index_file)
        }
        if args.json or not sys.stdout.isatty():
            print(json.dumps(error_data))
        else:
            logger.error(f"Source index file not found: {source_index_file}")
        sys.exit(2)

    if not target_index_file.exists():
        error_data = {
            "error": "missing_index_target",
            "object": args.object,
            "variant": args.variant,
            "expected_path": str(target_index_file)
        }
        if args.json or not sys.stdout.isatty():
            print(json.dumps(error_data))
        else:
            logger.error(f"Target index file not found: {target_index_file}")
        sys.exit(3)

    # Check if output exists and enforce --force policy
    if mapping_file.exists() and not args.force:
        error_data = {
            "error": "would_overwrite",
            "object": args.object,
            "variant": args.variant,
            "existing_file": str(mapping_file),
            "message": "Use --force to overwrite existing mapping.yaml"
        }
        if args.json or not sys.stdout.isatty():
            print(json.dumps(error_data))
        else:
            logger.error(f"Output file exists: {mapping_file}. Use --force to overwrite.")
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
                "error": "no_targets",
                "object": args.object,
                "variant": args.variant,
                "message": "No target fields found in index_target.yaml"
            }
            if args.json or not sys.stdout.isatty():
                print(json.dumps(error_data))
            else:
                logger.error("No target fields found in index_target.yaml")
            sys.exit(4)

        # Load central mapping memory (synonyms) if available
        synonyms = {}
        if central_mapping_file.exists():
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

        # Create output structure with exact key ordering
        output_data = {
            "metadata": mapping_result["metadata"],
            "mappings": mapping_result["mappings"],
            "to_audit": mapping_result["to_audit"],
            "unmapped_source_fields": mapping_result["unmapped_source_fields"],
            "unmapped_target_fields": mapping_result["unmapped_target_fields"]
        }

        # Write mapping.yaml with exact format
        mapping_file.parent.mkdir(parents=True, exist_ok=True)
        with open(mapping_file, "w", encoding="utf-8") as f:
            yaml.safe_dump(output_data, f, sort_keys=False, allow_unicode=True, default_flow_style=False)

        # Calculate metrics for logging
        mapped_count = len([m for m in mapping_result["mappings"] if m["status"] == "auto"])
        unmapped_count = len(mapping_result["unmapped_target_fields"])
        to_audit_count = len(mapping_result["to_audit"])
        unused_sources_count = len(mapping_result["unmapped_source_fields"])
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
            "warnings": []
        }

        # Add ruleset_sources to metadata if central mapping file exists
        if central_mapping_file.exists():
            output_data["metadata"]["ruleset_sources"] = str(central_mapping_file).replace("\\", "/")
            summary_data["ruleset_sources"] = str(central_mapping_file).replace("\\", "/")

        # Log JSONL summary and audit records
        if not args.quiet:
            if args.json or not sys.stdout.isatty():
                print(json.dumps(summary_data))
                # Log audit records for each target
                for mapping in mapping_result["mappings"]:
                    audit_data = {
                        "step": "map",
                        "target": f"S_{args.variant.upper()}.{mapping['target_field']}",
                        "decision": {
                            "source": mapping["source_header"],
                            "confidence": mapping["confidence"],
                            "status": mapping["status"],
                            "reason": mapping["rationale"]
                        },
                        "candidates": []  # Could add top-3 candidates here if we track them
                    }
                    print(json.dumps(audit_data))
            else:
                # Human preview format
                if not args.no_preview:
                    print("\n=== Mapping Preview (first 12) ===")
                    print(f"{'target_field':<20} | {'source_header':<25} | {'confidence':<10} | {'status':<10}")
                    print("-" * 75)
                    for i, mapping in enumerate(mapping_result["mappings"][:12]):
                        source_header = mapping["source_header"] or "null"
                        print(f"{mapping['target_field']:<20} | {source_header:<25} | {mapping['confidence']:<10.2f} | {mapping['status']:<10}")
                    if len(mapping_result["mappings"]) > 12:
                        print(f"... and {len(mapping_result['mappings']) - 12} more")
                
                print(f"\nmapped {mapped_count} • unmapped {unmapped_count} • to-audit {to_audit_count} • unused sources {unused_sources_count}")

        logger.info(f"Generated mapping.yaml: {mapping_file}")
        logger.info("✓ Map command completed successfully!")

    except Exception as e:
        error_data = {"error": "exception", "message": str(e)}
        if args.json or not sys.stdout.isatty():
            print(json.dumps(error_data))
        else:
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
        run_index_source_command(args, config)
    elif args.command == "index_target":
        run_index_target_command(args, config)
    elif args.command == "map":
        run_map_command(args, config)
    else:
        logger.error(f"Unknown command: {args.command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
