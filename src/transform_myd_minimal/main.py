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
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime

import pandas as pd
import yaml

from .cli import setup_cli
from .fuzzy import FuzzyConfig, FieldNormalizer, FuzzyMatcher
from .synonym import SynonymMatcher
from .generator import (
    read_excel_fields, generate_object_list_yaml, generate_fields_yaml, 
    generate_value_rules_yaml, generate_column_map_yaml, generate_migration_structure
)
from .logging_config import get_logger

# Initialize logger for this module
logger = get_logger(__name__)


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
    
    def match_fields(self, source_fields: pd.DataFrame, target_fields: pd.DataFrame) -> Tuple[List[FieldMatchResult], List[FieldMatchResult]]:
        """
        Match source fields to target fields using comprehensive strategies.
        
        Returns tuple of (matches, audit_matches) where:
        - matches: List of actual field mappings (exact and non-conflicting fuzzy)
        - audit_matches: List of fuzzy matches to already exact-mapped targets (for audit)
        """
        # Create normalized target lookup
        target_lookup = {}
        for _, target_row in target_fields.iterrows():
            target_name = target_row['field_name']
            target_desc = target_row['field_description']
            target_lookup[target_name] = {
                'description': target_desc,
                'normalized_name': self.normalizer.normalize_field_name(target_name),
                'normalized_desc': self.normalizer.normalize_description(target_desc),
                'is_key': target_row.get('field_is_key', False),
                'is_mandatory': target_row.get('field_is_mandatory', False)
            }
        
        # First pass: Find all exact matches
        exact_mapped_targets = set()
        results = []
        
        for _, source_row in source_fields.iterrows():
            source_name = source_row['field_name']
            source_desc = source_row['field_description']
            
            exact_match = self._find_exact_match(source_name, source_desc, target_lookup)
            if exact_match:
                results.append(exact_match)
                exact_mapped_targets.add(exact_match.target_field)
        
        # Second pass: Find fuzzy/synonym matches excluding already exact-mapped targets
        audit_matches = []
        
        for _, source_row in source_fields.iterrows():
            source_name = source_row['field_name']
            source_desc = source_row['field_description']
            
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
                results.append(FieldMatchResult(
                    source_field=source_name,
                    target_field=None,
                    confidence_score=0.0,
                    match_type="geen match",
                    reason="Geen geschikte match gevonden",
                    source_description=source_desc
                ))
            
            # Check for audit matches (fuzzy matches to exact-mapped targets)
            audit_match = self._find_audit_match(
                source_name, source_desc, target_lookup, exact_mapped_targets
            )
            if audit_match:
                audit_matches.append(audit_match)
        
        return results, audit_matches
    
    def _find_exact_match(self, source_name: str, source_desc: str, target_lookup: Dict) -> Optional[FieldMatchResult]:
        """Find exact match for a source field."""
        source_norm_name = self.normalizer.normalize_field_name(source_name)
        source_norm_desc = self.normalizer.normalize_description(source_desc)
        
        # Strategy 1: Exact match on normalized field names
        for target_name, target_info in target_lookup.items():
            if source_norm_name == target_info['normalized_name']:
                # Additional check: if descriptions are available, they should also match or be similar
                if source_norm_desc and target_info['normalized_desc']:
                    if source_norm_desc == target_info['normalized_desc']:
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
                    target_description=target_info['description']
                )
        return None
    
    def _find_fuzzy_match(self, source_name: str, source_desc: str, target_lookup: Dict, 
                         exact_mapped_targets: set) -> Optional[FieldMatchResult]:
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
                    target_description=target_info['description']
                )
            
            # Fuzzy matching
            if self.fuzzy_config.use_levenshtein or self.fuzzy_config.use_jaro_winkler:
                # Calculate name similarity
                name_sim_lev = self.fuzzy_matcher.levenshtein_similarity(
                    source_norm_name, target_info['normalized_name']
                ) if self.fuzzy_config.use_levenshtein else 0.0
                
                name_sim_jw = self.fuzzy_matcher.jaro_winkler_similarity(
                    source_norm_name, target_info['normalized_name']
                ) if self.fuzzy_config.use_jaro_winkler else 0.0
                
                # Combined name similarity
                name_similarity = (
                    name_sim_lev * self.fuzzy_config.levenshtein_weight +
                    name_sim_jw * self.fuzzy_config.jaro_winkler_weight
                )
                
                # Description similarity (if available)
                desc_similarity = 0.0
                if source_norm_desc and target_info['normalized_desc']:
                    desc_sim_lev = self.fuzzy_matcher.levenshtein_similarity(
                        source_norm_desc, target_info['normalized_desc']
                    ) if self.fuzzy_config.use_levenshtein else 0.0
                    
                    desc_sim_jw = self.fuzzy_matcher.jaro_winkler_similarity(
                        source_norm_desc, target_info['normalized_desc']
                    ) if self.fuzzy_config.use_jaro_winkler else 0.0
                    
                    desc_similarity = (
                        desc_sim_lev * self.fuzzy_config.levenshtein_weight +
                        desc_sim_jw * self.fuzzy_config.jaro_winkler_weight
                    )
                
                # Combined score: 70% name, 30% description
                if source_norm_desc and target_info['normalized_desc']:
                    combined_score = 0.7 * name_similarity + 0.3 * desc_similarity
                else:
                    combined_score = name_similarity
                
                if combined_score >= self.fuzzy_config.threshold and combined_score > best_score:
                    best_score = combined_score
                    algorithm = "levenshtein" if self.fuzzy_config.levenshtein_weight > self.fuzzy_config.jaro_winkler_weight else "jaro_winkler"
                    best_match = FieldMatchResult(
                        source_field=source_name,
                        target_field=target_name,
                        confidence_score=combined_score,
                        match_type="fuzzy",
                        reason=f"Fuzzy match (similarity: {combined_score:.2f})",
                        source_description=source_desc,
                        target_description=target_info['description'],
                        algorithm=algorithm
                    )
        
        return best_match
    
    def _find_audit_match(self, source_name: str, source_desc: str, target_lookup: Dict, 
                         exact_mapped_targets: set) -> Optional[FieldMatchResult]:
        """Find fuzzy matches to exact-mapped targets for audit purposes."""
        if not self.fuzzy_config.enabled or not exact_mapped_targets:
            return None
        
        source_norm_name = self.normalizer.normalize_field_name(source_name)
        source_norm_desc = self.normalizer.normalize_description(source_desc)
        
        best_match = None
        best_score = 0.0
        
        # Only check exact-mapped targets
        for target_name in exact_mapped_targets:
            target_info = target_lookup[target_name]
            
            # Calculate similarity to this exact-mapped target
            name_sim_lev = self.fuzzy_matcher.levenshtein_similarity(
                source_norm_name, target_info['normalized_name']
            ) if self.fuzzy_config.use_levenshtein else 0.0
            
            name_sim_jw = self.fuzzy_matcher.jaro_winkler_similarity(
                source_norm_name, target_info['normalized_name']
            ) if self.fuzzy_config.use_jaro_winkler else 0.0
            
            name_similarity = (
                name_sim_lev * self.fuzzy_config.levenshtein_weight +
                name_sim_jw * self.fuzzy_config.jaro_winkler_weight
            )
            
            if name_similarity >= self.fuzzy_config.threshold and name_similarity > best_score:
                best_score = name_similarity
                algorithm = "levenshtein" if self.fuzzy_config.levenshtein_weight > self.fuzzy_config.jaro_winkler_weight else "jaro_winkler"
                best_match = FieldMatchResult(
                    source_field=source_name,
                    target_field=target_name,
                    confidence_score=name_similarity,
                    match_type="audit",
                    reason=f"Fuzzy match to exact-mapped target (audit, similarity: {name_similarity:.2f})",
                    source_description=source_desc,
                    target_description=target_info['description'],
                    algorithm=algorithm
                )
        
        return best_match


def create_advanced_column_mapping(source_fields, target_fields, fuzzy_config=None, central_memory=None, object_name=None, variant=None):
    """Create advanced column mapping using comprehensive matching strategies with central mapping memory support."""
    
    # Initialize the advanced matcher
    matcher = AdvancedFieldMatcher(fuzzy_config)
    
    # Initialize tracking for central memory rules
    central_skip_matches = []
    central_manual_matches = []
    
    # Get effective rules from central mapping memory
    skip_rules, manual_mappings = get_effective_rules_for_table(central_memory, object_name or "", variant or "")
    
    # Apply skip rules first - remove skipped source fields
    filtered_source_fields = source_fields.copy()
    if skip_rules:
        skip_dict = {rule.source_field: rule for rule in skip_rules if rule.skip}
        
        for source_field in skip_dict:
            # Find matching rows in source_fields and mark for removal
            mask = filtered_source_fields['field_name'] == source_field
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
                    source_description=row.get('field_description', ''),
                    target_description=None,
                    algorithm="central_memory"
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
            mask = remaining_source_fields['field_name'] == source_field
            if mask.any():
                # Create manual mapping result for logging
                row = remaining_source_fields[mask].iloc[0]
                manual_result = FieldMatchResult(
                    source_field=source_field,
                    target_field=mapping.target,
                    confidence_score=1.0,
                    match_type="central_manual",
                    reason=f"Central memory manual mapping: {mapping.comment}",
                    source_description=row.get('field_description', ''),
                    target_description=mapping.target_description,
                    algorithm="central_memory"
                )
                central_manual_matches.append(manual_result)
                
                # Remove from source fields for further processing
                remaining_source_fields = remaining_source_fields[~mask]
    
    # Run advanced matching on remaining fields
    matches, audit_matches = matcher.match_fields(remaining_source_fields, target_fields)
    
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
    
    return mapping_lines, exact_matches, fuzzy_matches, unmapped_sources, audit_matches, central_skip_matches, central_manual_matches


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
        with open(central_memory_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        if not data:
            return None
        
        # Parse global skip fields
        global_skip_fields = []
        for skip_data in data.get('global_skip_fields', []):
            global_skip_fields.append(SkipRule(
                source_field=skip_data['source_field'],
                source_description=skip_data['source_description'],
                skip=skip_data['skip'],
                comment=skip_data['comment']
            ))
        
        # Parse global manual mappings
        global_manual_mappings = []
        for mapping_data in data.get('global_manual_mappings', []):
            global_manual_mappings.append(ManualMapping(
                source_field=mapping_data['source_field'],
                source_description=mapping_data['source_description'],
                target=mapping_data['target'],
                target_description=mapping_data['target_description'],
                comment=mapping_data['comment']
            ))
        
        # Parse table-specific rules (keep as dict for flexible processing)
        table_specific = data.get('table_specific', {})
        
        return CentralMappingMemory(
            global_skip_fields=global_skip_fields,
            global_manual_mappings=global_manual_mappings,
            table_specific=table_specific
        )
    
    except Exception as e:
        logger.warning(f"Could not load central mapping memory: {e}")
        return None


def get_effective_rules_for_table(central_memory: CentralMappingMemory, object_name: str, variant: str) -> Tuple[List[SkipRule], List[ManualMapping]]:
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
    table_skip_data = table_rules.get('skip_fields', [])
    for skip_data in table_skip_data:
        effective_skip_rules.append(SkipRule(
            source_field=skip_data['source_field'],
            source_description=skip_data['source_description'],
            skip=skip_data['skip'],
            comment=skip_data['comment']
        ))
    
    # Add table-specific manual mappings
    table_mapping_data = table_rules.get('manual_mappings', [])
    for mapping_data in table_mapping_data:
        effective_manual_mappings.append(ManualMapping(
            source_field=mapping_data['source_field'],
            source_description=mapping_data['source_description'],
            target=mapping_data['target'],
            target_description=mapping_data['target_description'],
            comment=mapping_data['comment']
        ))
    
    return effective_skip_rules, effective_manual_mappings


def run_index_source_command(args):
    """Run the index_source command - parse headers from XLSX and create index_source.yaml."""
    logger.info(f"=== Index Source Command: {args.object}/{args.variant} ===")
    
    # Construct input file path
    input_file = Path(f"data/03_raw/index_source_{args.object}_{args.variant}.xlsx")
    
    if not input_file.exists():
        logger.error(f"Input file not found: {input_file}")
        sys.exit(1)
    
    logger.info(f"Reading source headers from: {input_file}")
    
    # Read Excel file and parse headers
    try:
        df = pd.read_excel(input_file, header=0)
        headers = df.columns.tolist()
        
        logger.info(f"Found {len(headers)} source headers")
        
        # Create YAML structure
        source_data = {
            'metadata': {
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'source_file': str(input_file),
                'object': args.object,
                'variant': args.variant,
                'total_fields': len(headers),
                'generator': 'transform-myd-minimal index_source'
            },
            'source_fields': []
        }
        
        # Process each header
        for header in headers:
            source_data['source_fields'].append({
                'field_name': header,
                'field_description': header  # Use header as description if no separate description column
            })
        
        # Create output directory structure
        output_dir = Path(f"migrations/{args.object}/{args.variant}")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Write index_source.yaml
        output_file = output_dir / "index_source.yaml"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"# Source fields index generated by transform-myd-minimal\n")
            f.write(f"# Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            yaml.dump(source_data, f, default_flow_style=False, allow_unicode=True)
        
        logger.info(f"Generated index_source.yaml: {output_file}")
        
        # Update global object list
        update_object_list(args.object, args.variant)
        
        logger.info("✓ Index source command completed successfully!")
        
    except Exception as e:
        logger.error(f"Error processing source file: {e}")
        sys.exit(1)


def run_index_target_command(args):
    """Run the index_target command - parse XML and filter target fields by variant."""
    logger.info(f"=== Index Target Command: {args.object}/{args.variant} ===")
    
    # Construct input file path
    input_file = Path(f"data/03_raw/index_target_{args.object}_{args.variant}.xml")
    
    if not input_file.exists():
        logger.error(f"Input file not found: {input_file}")
        sys.exit(1)
    
    logger.info(f"Reading target fields from: {input_file}")
    
    try:
        # Use existing parsers to read XML
        from .parsers import SpreadsheetMLParser
        
        # Parse the XML file
        xml_parser = SpreadsheetMLParser(input_file)
        target_fields = xml_parser.parse_target_fields()
        
        # Filter fields that match the variant pattern (S_{variant})
        variant_pattern = f"S_{args.variant.upper()}"
        filtered_fields = []
        
        for field in target_fields:
            transformer_id = field.get('transformer_id', '')
            if transformer_id.startswith(variant_pattern):
                filtered_fields.append(field)
        
        logger.info(f"Found {len(filtered_fields)} target fields matching variant pattern '{variant_pattern}'")
        
        # Create YAML structure
        target_data = {
            'metadata': {
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'source_file': str(input_file),
                'object': args.object,
                'variant': args.variant,
                'variant_pattern': variant_pattern,
                'total_fields': len(filtered_fields),
                'generator': 'transform-myd-minimal index_target'
            },
            'target_fields': []
        }
        
        # Process each filtered field
        for field in filtered_fields:
            target_entry = {
                'internal_id': field.get('internal_id', ''),
                'transformer_id': field.get('transformer_id', ''),
                'sap_table': field.get('sap_table', ''),
                'sap_field': field.get('sap_field', ''),
                'description': field.get('description', ''),
                'group': field.get('group_name', ''),
                'importance': field.get('importance', ''),
                'type': field.get('type', ''),
                'length': field.get('length', ''),
                'decimal': field.get('decimal', '')
            }
            target_data['target_fields'].append(target_entry)
        
        # Create output directory structure
        output_dir = Path(f"migrations/{args.object}/{args.variant}")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Write index_target.yaml
        output_file = output_dir / "index_target.yaml"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"# Target fields index generated by transform-myd-minimal\n")
            f.write(f"# Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            yaml.dump(target_data, f, default_flow_style=False, allow_unicode=True)
        
        logger.info(f"Generated index_target.yaml: {output_file}")
        
        logger.info("✓ Index target command completed successfully!")
        
    except Exception as e:
        logger.error(f"Error processing target file: {e}")
        sys.exit(1)


def update_object_list(object_name: str, variant: str):
    """Update or create the global object_list.yaml file."""
    object_list_file = Path("migrations/object_list.yaml")
    
    # Load existing data if file exists
    object_list_data = {'objects': []}
    if object_list_file.exists():
        try:
            with open(object_list_file, 'r', encoding='utf-8') as f:
                existing_data = yaml.safe_load(f)
                if existing_data and 'objects' in existing_data:
                    object_list_data = existing_data
        except Exception:
            pass  # Use default structure if file is corrupted
    
    # Create object/variant entry
    entry_key = f"{object_name}_{variant}"
    
    # Check if this object/variant combination already exists
    existing_entries = [obj.get('key', '') for obj in object_list_data['objects']]
    if entry_key not in existing_entries:
        new_entry = {
            'key': entry_key,
            'object': object_name,
            'variant': variant,
            'path': f"migrations/{object_name}/{variant}/",
            'added_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        object_list_data['objects'].append(new_entry)
        
        # Write updated object list
        object_list_file.parent.mkdir(parents=True, exist_ok=True)
        with open(object_list_file, 'w', encoding='utf-8') as f:
            f.write(f"# Global object/variant list for transform-myd-minimal\n")
            f.write(f"# Updated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            yaml.dump(object_list_data, f, default_flow_style=False, allow_unicode=True)
        
        logger.info(f"Added {entry_key} to global object list: {object_list_file}")
    else:
        logger.info(f"Object/variant {entry_key} already exists in object list")


def run_map_command(args, config):
    """Run the map command - generates mapping from indexed source and target YAML files."""
    logger.info(f"=== Map Command: {args.object}/{args.variant} ===")
    
    # Check for indexed source and target files
    migrations_dir = Path(f"migrations/{args.object}/{args.variant}")
    source_index_file = migrations_dir / "index_source.yaml"
    target_index_file = migrations_dir / "index_target.yaml"
    
    if not source_index_file.exists():
        logger.error(f"Source index file not found: {source_index_file}")
        logger.info(f"Please run: ./transform-myd-minimal index_source --object {args.object} --variant {args.variant}")
        sys.exit(1)
    
    if not target_index_file.exists():
        logger.error(f"Target index file not found: {target_index_file}")
        logger.info(f"Please run: ./transform-myd-minimal index_target --object {args.object} --variant {args.variant}")
        sys.exit(1)
    
    logger.info(f"Reading source index from: {source_index_file}")
    logger.info(f"Reading target index from: {target_index_file}")
    
    try:
        # Load source fields from index_source.yaml
        with open(source_index_file, 'r', encoding='utf-8') as f:
            source_data = yaml.safe_load(f)
        
        # Load target fields from index_target.yaml
        with open(target_index_file, 'r', encoding='utf-8') as f:
            target_data = yaml.safe_load(f)
        
        # Convert to DataFrames for compatibility with existing matching logic
        source_fields_list = []
        for field in source_data.get('source_fields', []):
            source_fields_list.append({
                'field_name': field.get('field_name', ''),
                'field_description': field.get('field_description', '')
            })
        
        target_fields_list = []
        for field in target_data.get('target_fields', []):
            target_fields_list.append({
                'field_name': field.get('transformer_id', ''),
                'field_description': field.get('description', ''),
                'field_is_key': False,  # Default values for compatibility
                'field_is_mandatory': False
            })
        
        # Convert to DataFrames
        source_fields = pd.DataFrame(source_fields_list)
        target_fields = pd.DataFrame(target_fields_list)
        
        logger.info(f"Found {len(source_fields)} source fields and {len(target_fields)} target fields")
        
        # Load central mapping memory
        base_dir = Path.cwd()
        logger.info("Loading central mapping memory...")
        central_memory = load_central_mapping_memory(base_dir)
        if central_memory:
            logger.info("Central mapping memory loaded successfully")
            skip_rules, manual_mappings = get_effective_rules_for_table(central_memory, args.object, args.variant)
            logger.info(f"Found {len(skip_rules)} skip rules and {len(manual_mappings)} manual mappings for {args.object}_{args.variant}")
        else:
            logger.info("No central mapping memory found or failed to load")
        
        # Configure fuzzy matching using config values
        fuzzy_config = FuzzyConfig(
            enabled=not config.disable_fuzzy,
            threshold=config.fuzzy_threshold,
            max_suggestions=config.max_suggestions
        )
        
        # Create advanced mapping with central memory support
        mapping_result = create_advanced_column_mapping(
            source_fields, target_fields, fuzzy_config, central_memory, args.object, args.variant
        )
        mapping_lines, exact_matches, fuzzy_matches, unmapped_sources, audit_matches, central_skip_matches, central_manual_matches = mapping_result
        
        # Print matching statistics
        logger.info("")
        logger.info("=== Advanced Matching Results ===")
        if central_skip_matches:
            logger.info(f"Central memory skip rules applied: {len(central_skip_matches)}")
        if central_manual_matches:
            logger.info(f"Central memory manual mappings applied: {len(central_manual_matches)}")
        logger.info(f"Exact matches: {len(exact_matches)}")
        logger.info(f"Fuzzy/Synonym matches: {len(fuzzy_matches)}")
        logger.info(f"Unmapped sources: {len(unmapped_sources)}")
        logger.info(f"Audit matches (fuzzy to exact-mapped targets): {len(audit_matches)}")
        logger.info(f"Mapping coverage: {((len(exact_matches) + len(fuzzy_matches)) / len(source_fields) * 100):.1f}%")
        
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
                logger.info(f"  MANUAL: {match.source_field} → {match.target_field} - {match.reason}")
        
        if fuzzy_matches:
            logger.info("")
            logger.info("Fuzzy/Synonym matches found:")
            for match in fuzzy_matches:
                logger.info(f"  {match.source_field} → {match.target_field} ({match.match_type}, confidence: {match.confidence_score:.2f})")
        
        if audit_matches:
            logger.info("")
            logger.info("Audit matches found (fuzzy matches to exact-mapped targets):")
            for match in audit_matches:
                logger.info(f"  {match.source_field} → {match.target_field} (audit, confidence: {match.confidence_score:.2f})")
        
        # Generate mapping.yaml
        mapping_data = {
            'metadata': {
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'object': args.object,
                'variant': args.variant,
                'source_index': str(source_index_file),
                'target_index': str(target_index_file),
                'total_mappings': len(exact_matches) + len(fuzzy_matches) + len(central_manual_matches),
                'coverage_percentage': ((len(exact_matches) + len(fuzzy_matches) + len(central_manual_matches)) / len(source_fields) * 100) if source_fields.shape[0] > 0 else 0,
                'generator': 'transform-myd-minimal map'
            },
            'mappings': [],
            'unmapped_sources': [],
            'audit_matches': []
        }
        
        # Add all mappings
        all_matches = central_manual_matches + exact_matches + fuzzy_matches
        for match in all_matches:
            if match.target_field:
                mapping_entry = {
                    'source_field': match.source_field,
                    'target_field': match.target_field,
                    'confidence_score': match.confidence_score,
                    'match_type': match.match_type,
                    'reason': match.reason,
                    'source_description': match.source_description,
                    'target_description': match.target_description
                }
                if match.algorithm:
                    mapping_entry['algorithm'] = match.algorithm
                mapping_data['mappings'].append(mapping_entry)
        
        # Add unmapped sources
        for unmapped in unmapped_sources:
            mapping_data['unmapped_sources'].append({
                'source_field': unmapped.source_field,
                'reason': unmapped.reason,
                'source_description': unmapped.source_description
            })
        
        # Add audit matches
        for audit in audit_matches:
            mapping_data['audit_matches'].append({
                'source_field': audit.source_field,
                'target_field': audit.target_field,
                'confidence_score': audit.confidence_score,
                'reason': audit.reason,
                'algorithm': audit.algorithm
            })
        
        # Write mapping.yaml
        output_file = migrations_dir / "mapping.yaml"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"# Source-to-target field mappings generated by transform-myd-minimal\n")
            f.write(f"# Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# Coverage: {mapping_data['metadata']['coverage_percentage']:.1f}%\n\n")
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
    if args.command == 'index_source':
        run_index_source_command(args)
    elif args.command == 'index_target':
        run_index_target_command(args)
    elif args.command == 'map':
        run_map_command(args, config)
    else:
        logger.error(f"Unknown command: {args.command}")
        sys.exit(1)


if __name__ == "__main__":
    main()