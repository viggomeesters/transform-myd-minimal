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

import pandas as pd
import yaml

from .cli import setup_cli
from .fuzzy import FuzzyConfig, FieldNormalizer, FuzzyMatcher
from .synonym import SynonymMatcher
from .generator import (
    read_excel_fields, generate_object_list_yaml, generate_fields_yaml, 
    generate_value_rules_yaml, generate_column_map_yaml, generate_migration_structure
)


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
        print(f"Warning: Could not load central mapping memory: {e}")
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


def run_map_command(args, config):
    """Run the map command - generates column mapping and YAML files."""
    # Construct paths using configuration
    base_dir = Path.cwd()
    excel_path = config.get_input_path(args.object, args.variant)
    
    # Output path using configuration
    output_dir = config.get_output_dir(args.object, args.variant)
    output_path = output_dir / "column_map.yaml"
    
    try:
        # Load central mapping memory
        print("Loading central mapping memory...")
        central_memory = load_central_mapping_memory(base_dir)
        if central_memory:
            print("Central mapping memory loaded successfully")
            skip_rules, manual_mappings = get_effective_rules_for_table(central_memory, args.object, args.variant)
            print(f"Found {len(skip_rules)} skip rules and {len(manual_mappings)} manual mappings for {args.object}_{args.variant}")
        else:
            print("No central mapping memory found or failed to load")
        
        # Read Excel file
        print(f"Reading Excel file: {excel_path}")
        source_fields, target_fields = read_excel_fields(excel_path)
        
        print(f"Found {len(source_fields)} source fields and {len(target_fields)} target fields")
        print("Initializing advanced field matching system...")
        
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
        print("\n=== Advanced Matching Results ===")
        if central_skip_matches:
            print(f"Central memory skip rules applied: {len(central_skip_matches)}")
        if central_manual_matches:
            print(f"Central memory manual mappings applied: {len(central_manual_matches)}")
        print(f"Exact matches: {len(exact_matches)}")
        print(f"Fuzzy/Synonym matches: {len(fuzzy_matches)}")
        print(f"Unmapped sources: {len(unmapped_sources)}")
        print(f"Audit matches (fuzzy to exact-mapped targets): {len(audit_matches)}")
        print(f"Mapping coverage: {((len(exact_matches) + len(fuzzy_matches)) / len(source_fields) * 100):.1f}%")
        
        # Show central memory rule applications
        if central_skip_matches:
            print("\nCentral memory skip rules applied:")
            for match in central_skip_matches:
                print(f"  SKIP: {match.source_field} - {match.reason}")
        
        if central_manual_matches:
            print("\nCentral memory manual mappings applied:")
            for match in central_manual_matches:
                print(f"  MANUAL: {match.source_field} → {match.target_field} - {match.reason}")
        
        if fuzzy_matches:
            print("\nFuzzy/Synonym matches found:")
            for match in fuzzy_matches:
                print(f"  {match.source_field} → {match.target_field} ({match.match_type}, confidence: {match.confidence_score:.2f})")
        
        if audit_matches:
            print("\nAudit matches found (fuzzy matches to exact-mapped targets):")
            for match in audit_matches:
                print(f"  {match.source_field} → {match.target_field} (audit, confidence: {match.confidence_score:.2f})")
        
        # Generate YAML content with central memory data
        excel_filename = f"fields_{args.object}_{args.variant}.xlsx"
        excel_relative_path = f".\\{config.input_dir}\\{excel_filename}"
        yaml_content = generate_column_map_yaml(args.object, args.variant, source_fields, target_fields, 
                                              excel_relative_path, audit_matches, central_skip_matches, central_manual_matches)
        
        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Write the column mapping file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(yaml_content)
        
        print(f"\nGenerated advanced column mapping: {output_path}")
        
        # Read the Excel file into a DataFrame for YAML generation
        df = pd.read_excel(excel_path)
        
        # Generate additional YAML files
        print("\n=== Generating Additional YAML Files ===")
        
        # Generate object_list.yaml (updated with current structure)
        generate_object_list_yaml(base_dir, config.output_dir)
        
        # Generate fields.yaml for current table
        generate_fields_yaml(base_dir, args.object, args.variant, df, config.output_dir, config.input_dir)
        
        # Generate value_rules.yaml for current table
        generate_value_rules_yaml(base_dir, args.object, args.variant, df, config.output_dir, config.input_dir)
        
        print("\nAll YAML files generated successfully!")
        
        # === Generate New Multi-File Migration Structure ===
        print(f"\n=== Generating New Multi-File Migration Structure ===")
        try:
            generated_migration_files = generate_migration_structure(base_dir, args.object, args.variant, df)
            if generated_migration_files:
                print(f"Generated {len(generated_migration_files)} migration files in migrations/ directory")
                print("New structure provides:")
                print("  ✓ Clear separation of concerns (fields, mappings, validation, transformations)")
                print("  ✓ Non-redundant field definitions")
                print("  ✓ SAP object-anchored structure")
                print("  ✓ Table-scoped value rules (not object-wide)")
                print("  ✓ Auditable mapping decisions")
            else:
                print("Migration structure generation skipped (no data)")
        except Exception as e:
            print(f"Warning: Could not generate migration structure: {e}")
            print("Legacy YAML files are still available in config/ directory")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main entry point for the application."""
    args, config, is_legacy = setup_cli()
    
    # Execute the map command
    run_map_command(args, config)


if __name__ == "__main__":
    main()