#!/usr/bin/env python3
"""
transform-myd-minimal: Generate column mapping YAML from Excel field definitions

Advanced automatic field matching system for transform-myd.

Implements comprehensive matching strategies as specified in the requirements:
- Exact match on normalized field names and descriptions
- Synonym matching with expandable NL/EN synonym list
- Fuzzy matching using Levenshtein and Jaro-Winkler algorithms
- Configurable thresholds and top-N suggestions
- Confidence scores: "exact", "synoniem", "fuzzy", "geen match"
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import pandas as pd
import yaml


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
class FuzzyConfig:
    """Configuration for fuzzy matching behavior."""
    enabled: bool = True
    threshold: float = 0.6  # Minimum similarity score for suggestions
    max_suggestions: int = 3  # Maximum number of suggestions to return
    levenshtein_weight: float = 0.5  # Weight for Levenshtein algorithm
    jaro_winkler_weight: float = 0.5  # Weight for Jaro-Winkler algorithm
    use_levenshtein: bool = True
    use_jaro_winkler: bool = True


class FieldNormalizer:
    """Normalizes field names and descriptions for matching."""
    
    @staticmethod
    def normalize_field_name(name: str) -> str:
        """
        Normalize field name according to problem statement examples:
        - Remove accents and special characters
        - Convert to lowercase
        - Remove spaces, underscores, hyphens
        """
        if not name:
            return ""
        
        # Remove accents and convert to ASCII
        normalized = unicodedata.normalize('NFD', name)
        ascii_text = normalized.encode('ascii', 'ignore').decode('ascii')
        
        # Convert to lowercase and remove special characters
        cleaned = re.sub(r'[^a-zA-Z0-9]', '', ascii_text.lower())
        
        return cleaned
    
    @staticmethod
    def normalize_description(description: str) -> str:
        """
        Normalize field description for matching:
        - Remove accents and special characters
        - Convert to lowercase
        - Remove extra whitespace
        """
        if not description:
            return ""
        
        # Remove accents and convert to ASCII
        normalized = unicodedata.normalize('NFD', description)
        ascii_text = normalized.encode('ascii', 'ignore').decode('ascii')
        
        # Convert to lowercase and normalize whitespace
        cleaned = re.sub(r'\s+', ' ', ascii_text.lower().strip())
        
        return cleaned


class FuzzyMatcher:
    """Implements fuzzy string matching algorithms."""
    
    @staticmethod
    def levenshtein_distance(s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings."""
        if len(s1) < len(s2):
            return FuzzyMatcher.levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    @staticmethod
    def levenshtein_similarity(s1: str, s2: str) -> float:
        """Calculate Levenshtein similarity (0.0 to 1.0)."""
        if not s1 and not s2:
            return 1.0
        if not s1 or not s2:
            return 0.0
        
        max_len = max(len(s1), len(s2))
        distance = FuzzyMatcher.levenshtein_distance(s1, s2)
        return 1.0 - (distance / max_len)
    
    @staticmethod
    def jaro_winkler_similarity(s1: str, s2: str) -> float:
        """Calculate Jaro-Winkler similarity (0.0 to 1.0)."""
        if not s1 and not s2:
            return 1.0
        if not s1 or not s2:
            return 0.0
        
        # Jaro similarity
        jaro_sim = FuzzyMatcher._jaro_similarity(s1, s2)
        
        # Winkler modification
        prefix_len = 0
        for i in range(min(len(s1), len(s2), 4)):
            if s1[i] == s2[i]:
                prefix_len += 1
            else:
                break
        
        return jaro_sim + (0.1 * prefix_len * (1 - jaro_sim))
    
    @staticmethod
    def _jaro_similarity(s1: str, s2: str) -> float:
        """Calculate Jaro similarity."""
        len1, len2 = len(s1), len(s2)
        if len1 == 0 and len2 == 0:
            return 1.0
        if len1 == 0 or len2 == 0:
            return 0.0
        
        # Maximum allowed distance
        match_distance = (max(len1, len2) // 2) - 1
        if match_distance < 0:
            match_distance = 0
        
        # Initialize match arrays
        s1_matches = [False] * len1
        s2_matches = [False] * len2
        
        matches = 0
        transpositions = 0
        
        # Find matches
        for i in range(len1):
            start = max(0, i - match_distance)
            end = min(i + match_distance + 1, len2)
            
            for j in range(start, end):
                if s2_matches[j] or s1[i] != s2[j]:
                    continue
                s1_matches[i] = s2_matches[j] = True
                matches += 1
                break
        
        if matches == 0:
            return 0.0
        
        # Count transpositions
        k = 0
        for i in range(len1):
            if not s1_matches[i]:
                continue
            while not s2_matches[k]:
                k += 1
            if s1[i] != s2[k]:
                transpositions += 1
            k += 1
        
        return (matches / len1 + matches / len2 + (matches - transpositions / 2) / matches) / 3


class SynonymMatcher:
    """Handles synonym matching for NL/EN terms."""
    
    # Expandable synonym dictionary (NL/EN)
    SYNONYMS = {
        # Common business terms
        "klant": ["customer", "client", "kunde"],
        "naam": ["name", "naam", "bezeichnung"],
        "adres": ["address", "adresse"],
        "land": ["country", "land", "pais"],
        "bedrag": ["amount", "betrag", "montant"],
        "datum": ["date", "datum", "fecha"],
        "nummer": ["number", "nummer", "numero"],
        "code": ["code", "kode"],
        "beschrijving": ["description", "beschreibung", "descripcion"],
        "status": ["status", "staat"],
        "actief": ["active", "aktiv"],
        "blokkeren": ["block", "blockieren"],
        "vlag": ["flag", "flagge"],
        "controle": ["control", "kontrolle"],
        "indicatie": ["indicator", "indikator"],
        
        # Banking specific terms
        "bank": ["bank", "banco"],
        "rekening": ["account", "konto", "cuenta"],
        "saldo": ["balance", "saldo"],
        "transactie": ["transaction", "transaktion"],
        "betaling": ["payment", "zahlung", "pago"],
        "overboekingen": ["transfer", "uberweisung"],
        
        # Technical terms
        "sleutel": ["key", "schlussel", "clave"],
        "waarde": ["value", "wert", "valor"],
        "type": ["type", "typ", "tipo"],
        "referentie": ["reference", "referenz", "referencia"],
        "versie": ["version", "version"],
        "configuratie": ["configuration", "konfiguration"]
    }
    
    @classmethod
    def find_synonyms(cls, term: str) -> List[str]:
        """Find synonyms for a given term."""
        term_normalized = FieldNormalizer.normalize_field_name(term)
        synonyms = []
        
        for key, values in cls.SYNONYMS.items():
            key_normalized = FieldNormalizer.normalize_field_name(key)
            if term_normalized == key_normalized:
                synonyms.extend([FieldNormalizer.normalize_field_name(v) for v in values])
                break
                
            for value in values:
                value_normalized = FieldNormalizer.normalize_field_name(value)
                if term_normalized == value_normalized:
                    synonyms.append(key_normalized)
                    synonyms.extend([FieldNormalizer.normalize_field_name(v) for v in values if v != value])
                    break
        
        return list(set(synonyms))
    
    @classmethod
    def is_synonym_match(cls, term1: str, term2: str) -> bool:
        """Check if two terms are synonyms."""
        term1_norm = FieldNormalizer.normalize_field_name(term1)
        term2_norm = FieldNormalizer.normalize_field_name(term2)
        
        if term1_norm == term2_norm:
            return True
            
        synonyms1 = cls.find_synonyms(term1)
        synonyms2 = cls.find_synonyms(term2)
        
        return term2_norm in synonyms1 or term1_norm in synonyms2


class AdvancedFieldMatcher:
    """Advanced field matching system with multiple strategies."""
    
    def __init__(self, fuzzy_config: Optional[FuzzyConfig] = None):
        self.fuzzy_config = fuzzy_config or FuzzyConfig()
        self.normalizer = FieldNormalizer()
        self.fuzzy_matcher = FuzzyMatcher()
        self.synonym_matcher = SynonymMatcher()
    
    def match_fields(self, source_fields: pd.DataFrame, target_fields: pd.DataFrame) -> List[FieldMatchResult]:
        """
        Match source fields to target fields using comprehensive strategies.
        
        Returns list of FieldMatchResult objects with confidence scores and reasoning.
        """
        results = []
        
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
        
        # Process each source field
        for _, source_row in source_fields.iterrows():
            source_name = source_row['field_name']
            source_desc = source_row['field_description']
            
            match_result = self._find_best_match(
                source_name, source_desc, target_lookup
            )
            results.append(match_result)
        
        return results
    
    def _find_best_match(self, source_name: str, source_desc: str, target_lookup: Dict) -> FieldMatchResult:
        """Find the best match for a source field using multiple strategies."""
        
        source_norm_name = self.normalizer.normalize_field_name(source_name)
        source_norm_desc = self.normalizer.normalize_description(source_desc)
        
        # Strategy 1: Exact match on normalized field names
        for target_name, target_info in target_lookup.items():
            if source_norm_name == target_info['normalized_name']:
                # Check if descriptions also match for higher confidence
                desc_match = source_norm_desc == target_info['normalized_desc']
                confidence = 1.0 if desc_match else 0.95
                reason = "Exacte naam + identieke beschrijving" if desc_match else "Exacte veldnaam match"
                
                return FieldMatchResult(
                    source_field=source_name,
                    target_field=target_name,
                    confidence_score=confidence,
                    match_type="exact",
                    reason=reason,
                    source_description=source_desc,
                    target_description=target_info['description']
                )
        
        # Strategy 2: Synonym matching
        synonym_matches = []
        for target_name, target_info in target_lookup.items():
            if self.synonym_matcher.is_synonym_match(source_name, target_name):
                synonym_matches.append((target_name, target_info, 0.85))
        
        if synonym_matches:
            # Take the first synonym match (could be enhanced with ranking)
            target_name, target_info, confidence = synonym_matches[0]
            return FieldMatchResult(
                source_field=source_name,
                target_field=target_name,
                confidence_score=confidence,
                match_type="synoniem",
                reason="Synoniem match gevonden",
                source_description=source_desc,
                target_description=target_info['description']
            )
        
        # Strategy 3: Fuzzy matching
        if self.fuzzy_config.enabled:
            fuzzy_matches = []
            
            for target_name, target_info in target_lookup.items():
                # Fuzzy match on field names
                name_similarity = self._calculate_fuzzy_similarity(
                    source_norm_name, target_info['normalized_name']
                )
                
                # Fuzzy match on descriptions
                desc_similarity = self._calculate_fuzzy_similarity(
                    source_norm_desc, target_info['normalized_desc']
                )
                
                # Combined similarity (weighted average)
                combined_similarity = (name_similarity * 0.7) + (desc_similarity * 0.3)
                
                if combined_similarity >= self.fuzzy_config.threshold:
                    fuzzy_matches.append((
                        target_name, target_info, combined_similarity, 
                        name_similarity, desc_similarity
                    ))
            
            if fuzzy_matches:
                # Sort by similarity and take the best match
                fuzzy_matches.sort(key=lambda x: x[2], reverse=True)
                best_match = fuzzy_matches[0]
                target_name, target_info, combined_sim, name_sim, desc_sim = best_match
                
                # Determine which algorithm contributed most
                algorithm = "combined"
                if name_sim > desc_sim:
                    algorithm = "name_fuzzy"
                else:
                    algorithm = "description_fuzzy"
                
                return FieldMatchResult(
                    source_field=source_name,
                    target_field=target_name,
                    confidence_score=combined_sim,
                    match_type="fuzzy",
                    reason=f"Fuzzy match (similarity: {combined_sim:.2f})",
                    source_description=source_desc,
                    target_description=target_info['description'],
                    algorithm=algorithm
                )
        
        # No match found
        return FieldMatchResult(
            source_field=source_name,
            target_field=None,
            confidence_score=0.0,
            match_type="geen match",
            reason="Geen geschikte match gevonden",
            source_description=source_desc
        )
    
    def _calculate_fuzzy_similarity(self, str1: str, str2: str) -> float:
        """Calculate combined fuzzy similarity using configured algorithms."""
        if not str1 or not str2:
            return 0.0
        
        similarities = []
        
        if self.fuzzy_config.use_levenshtein:
            lev_sim = self.fuzzy_matcher.levenshtein_similarity(str1, str2)
            similarities.append(lev_sim * self.fuzzy_config.levenshtein_weight)
        
        if self.fuzzy_config.use_jaro_winkler:
            jw_sim = self.fuzzy_matcher.jaro_winkler_similarity(str1, str2)
            similarities.append(jw_sim * self.fuzzy_config.jaro_winkler_weight)
        
        if not similarities:
            return 0.0
        
        # Weighted average
        total_weight = 0
        if self.fuzzy_config.use_levenshtein:
            total_weight += self.fuzzy_config.levenshtein_weight
        if self.fuzzy_config.use_jaro_winkler:
            total_weight += self.fuzzy_config.jaro_winkler_weight
        
        return sum(similarities) / total_weight if total_weight > 0 else 0.0


def read_excel_fields(excel_path):
    """Read the Excel file and extract source and target fields"""
    try:
        df = pd.read_excel(excel_path)
    except FileNotFoundError:
        raise FileNotFoundError(f"Excel file not found: {excel_path}")
    except Exception as e:
        raise Exception(f"Error reading Excel file: {e}")
    
    # Split into source and target fields
    source_fields = df[df['field'] == 'Source'].copy()
    target_fields = df[df['field'] == 'Target'].copy()
    
    return source_fields, target_fields


def create_advanced_column_mapping(source_fields, target_fields, fuzzy_config=None):
    """Create advanced column mapping using comprehensive matching strategies."""
    
    # Initialize the advanced matcher
    matcher = AdvancedFieldMatcher(fuzzy_config)
    
    # Get match results
    match_results = matcher.match_fields(source_fields, target_fields)
    
    # Create mapping lines based on results
    mapping_lines = []
    exact_matches = []
    fuzzy_matches = []
    unmapped_sources = []
    
    for result in match_results:
        if result.target_field:
            if result.match_type == "exact":
                mapping_lines.append(f"{result.source_field}: {result.target_field}")
                exact_matches.append(result)
            else:
                mapping_lines.append(f"{result.source_field}: {result.target_field}")
                fuzzy_matches.append(result)
        else:
            unmapped_sources.append(result)
    
    # Add derived targets (targets without source mapping)
    mapped_targets = {result.target_field for result in match_results if result.target_field}
    for _, target_row in target_fields.iterrows():
        target_name = target_row['field_name']
        if target_name not in mapped_targets:
            mapping_lines.append(f"<NOT_IN_SOURCE_{target_name}>: {target_name}")
    
    return mapping_lines, exact_matches, fuzzy_matches, unmapped_sources


def create_column_mapping(source_fields, target_fields):
    """Legacy column mapping function - maintained for backward compatibility."""
    mapping_lines, _, _, _ = create_advanced_column_mapping(source_fields, target_fields)
    return mapping_lines


def is_constant_field(field_name, field_description):
    """
    Determine if a derived target field should be marked as constant.
    
    Args:
        field_name (str): The name of the field
        field_description (str): The description of the field
    
    Returns:
        bool: True if field should be marked as constant, False otherwise
    """
    # Convert to lowercase for case-insensitive matching
    name_lower = field_name.lower()
    desc_lower = field_description.lower()
    
    # Operational flag patterns in field names
    operational_name_patterns = [
        'overwrite', 'flag', 'control', 'indicator', 'switch', 
        'enable', 'disable', 'active', 'status'
    ]
    
    # Operational flag patterns in descriptions
    operational_desc_patterns = [
        'overwrite', 'flag', 'operational', 'control', 'indicator',
        'do not', 'block', 'prevent', 'enable', 'disable',
        'switch', 'toggle', 'status'
    ]
    
    # Check field name patterns
    for pattern in operational_name_patterns:
        if pattern in name_lower:
            return True
    
    # Check description patterns
    for pattern in operational_desc_patterns:
        if pattern in desc_lower:
            return True
    
    return False


def scan_data_structure(base_path):
    """Scan data/config/{object}/{variant} structure to find all objects and tables."""
    objects = {}
    config_path = base_path / "data" / "config"
    
    if not config_path.exists():
        print(f"Warning: {config_path} does not exist")
        return {}
    
    # Scan for objects and variants
    for object_dir in config_path.iterdir():
        if object_dir.is_dir() and not object_dir.name.startswith('.'):
            object_name = object_dir.name
            tables = []
            
            for variant_dir in object_dir.iterdir():
                if variant_dir.is_dir() and not variant_dir.name.startswith('.'):
                    tables.append(variant_dir.name)
            
            if tables:
                objects[object_name] = sorted(tables)
    
    return objects


def generate_object_list_yaml(base_path):
    """Generate config/object_list.yaml with overview of all objects and tables."""
    objects_structure = scan_data_structure(base_path)
    
    # Format for YAML output
    yaml_data = {
        'Objects': []
    }
    
    for object_name, tables in objects_structure.items():
        yaml_data['Objects'].append({
            'object': object_name,
            'tables': tables
        })
    
    # Write to file
    output_path = base_path / "data" / "config" / "object_list.yaml"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"# Generated by transform-myd-minimal @ {datetime.now().strftime('%Y%m%d %H%M')}\n")
        f.write("# Overview of all objects and their tables\n\n")
        yaml.dump(yaml_data, f, default_flow_style=False, allow_unicode=True)
    
    print(f"Generated: {output_path}")
    return output_path


def determine_field_type(field_data):
    """Determine field type based on field properties."""
    # Default type
    field_type = "string"
    
    # You can extend this logic based on field naming patterns or descriptions
    field_name = field_data.get('field_name', '').lower()
    field_desc = field_data.get('field_description', '').lower()
    
    if any(keyword in field_name for keyword in ['date', 'dat', 'time']):
        field_type = "date"
    elif any(keyword in field_name for keyword in ['amount', 'amt', 'value', 'val']):
        field_type = "decimal"
    elif any(keyword in field_name for keyword in ['count', 'number', 'num', 'id']):
        field_type = "integer"
    elif any(keyword in field_desc for keyword in ['boolean', 'flag', 'indicator']):
        field_type = "boolean"
    
    return field_type


def is_operational_field(field_name, field_description):
    """Determine if a field is operational based on name/description patterns."""
    operational_patterns = [
        'flag', 'status', 'indicator', 'control', 'system', 'process',
        'update', 'created', 'modified', 'version', 'lock'
    ]
    
    field_text = f"{field_name} {field_description}".lower()
    return any(pattern in field_text for pattern in operational_patterns)


def is_derived_field(field_name, field_description):
    """Determine if a field is derived based on name/description patterns."""
    derived_patterns = [
        'calculated', 'computed', 'derived', 'total', 'sum', 'average',
        'balance', 'amount', 'percentage', 'ratio'
    ]
    
    field_text = f"{field_name} {field_description}".lower()
    return any(pattern in field_text for pattern in derived_patterns)


def generate_fields_yaml(base_path, object_name, variant, df):
    """Generate fields.yaml for a specific table (object/variant combination)."""
    if df is None:
        return None
    
    # Filter for target fields (these are the output fields)
    target_fields = df[df['field'] == 'Target'].copy()
    
    # Generate fields YAML structure
    fields_data = {
        'table': f"{object_name}_{variant}",
        'fields': []
    }
    
    for _, row in target_fields.iterrows():
        field_info = {
            'name': row.get('field_name', ''),
            'description': row.get('field_description', ''),
            'type': determine_field_type(row),
            'required': bool(row.get('field_is_mandatory', False)),
            'key': bool(row.get('field_is_key', False))
        }
        fields_data['fields'].append(field_info)
    
    # Write to file
    excel_filename = f"fields_{object_name}_{variant}.xlsx"
    output_path = base_path / "data" / "config" / object_name / variant / "fields.yaml"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"# Generated by transform-myd-minimal @ {datetime.now().strftime('%Y%m%d %H%M')}\n")
        f.write(f"# Field definitions for {object_name}_{variant}\n")
        f.write(f"# Source: data/02_fields/{excel_filename}\n\n")
        yaml.dump(fields_data, f, default_flow_style=False, allow_unicode=True)
    
    print(f"Generated: {output_path}")
    return output_path


def generate_value_rules_yaml(base_path, object_name, variant, df):
    """Generate value_rules.yaml for a specific table."""
    if df is None:
        return None
    
    # Filter for target fields
    target_fields = df[df['field'] == 'Target'].copy()
    
    # Generate rules YAML structure
    rules_data = {
        'table': f"{object_name}_{variant}",
        'value_rules': []
    }
    
    for _, row in target_fields.iterrows():
        field_name = row.get('field_name', '')
        field_description = row.get('field_description', '')
        is_mandatory = bool(row.get('field_is_mandatory', False))
        
        rule_info = {
            'field': field_name,
            'description': field_description
        }
        
        # Determine rule type based on field properties
        if is_mandatory:
            rule_info['rule'] = 'required'
            rule_info['reason'] = 'Mandatory field as per data specification'
        elif is_operational_field(field_name, field_description):
            rule_info['rule'] = 'constant'
            rule_info['value'] = ' '  # Empty/blank default
            rule_info['reason'] = 'Operational field; no semantic source in source data'
        elif is_derived_field(field_name, field_description):
            rule_info['rule'] = 'derive'
            rule_info['reason'] = 'Derived field; requires business logic implementation'
        else:
            rule_info['rule'] = 'map'
            rule_info['reason'] = 'Direct mapping from source field'
        
        rules_data['value_rules'].append(rule_info)
    
    # Write to file
    excel_filename = f"fields_{object_name}_{variant}.xlsx"
    output_path = base_path / "data" / "config" / object_name / variant / "value_rules.yaml"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"# Generated by transform-myd-minimal @ {datetime.now().strftime('%Y%m%d %H%M')}\n")
        f.write(f"# Value rules for {object_name}_{variant}\n")
        f.write(f"# Rules: required, constant, derive, map\n")
        f.write(f"# Source: data/02_fields/{excel_filename}\n\n")
        yaml.dump(rules_data, f, default_flow_style=False, allow_unicode=True)
    
    print(f"Generated: {output_path}")
    return output_path


def run_map_command(args):
    """Run the map command - generates column mapping and YAML files."""
    # Construct paths
    base_dir = Path.cwd()
    excel_filename = f"fields_{args.object}_{args.variant}.xlsx"
    excel_path = base_dir / "data" / "02_fields" / excel_filename
    
    # Output path
    output_dir = base_dir / "data" / "config" / args.object / args.variant
    output_path = output_dir / "column_map.yaml"
    
    try:
        # Read Excel file
        print(f"Reading Excel file: {excel_path}")
        source_fields, target_fields = read_excel_fields(excel_path)
        
        print(f"Found {len(source_fields)} source fields and {len(target_fields)} target fields")
        print("Initializing advanced field matching system...")
        
        # Configure fuzzy matching
        fuzzy_config = FuzzyConfig(
            enabled=not args.disable_fuzzy,
            threshold=args.fuzzy_threshold,
            max_suggestions=args.max_suggestions
        )
        
        # Create advanced mapping to get statistics
        mapping_lines, exact_matches, fuzzy_matches, unmapped_sources = create_advanced_column_mapping(
            source_fields, target_fields, fuzzy_config
        )
        
        # Print matching statistics
        print("\n=== Advanced Matching Results ===")
        print(f"Exact matches: {len(exact_matches)}")
        print(f"Fuzzy/Synonym matches: {len(fuzzy_matches)}")
        print(f"Unmapped sources: {len(unmapped_sources)}")
        print(f"Mapping coverage: {((len(exact_matches) + len(fuzzy_matches)) / len(source_fields) * 100):.1f}%")
        
        if fuzzy_matches:
            print("\nFuzzy/Synonym matches found:")
            for match in fuzzy_matches:
                print(f"  {match.source_field} → {match.target_field} ({match.match_type}, confidence: {match.confidence_score:.2f})")
        
        # Generate YAML content
        yaml_content = generate_column_map_yaml(args.object, args.variant, source_fields, target_fields, 
                                              f".\\data\\02_fields\\{excel_filename}")
        
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
        generate_object_list_yaml(base_dir)
        
        # Generate fields.yaml for current table
        generate_fields_yaml(base_dir, args.object, args.variant, df)
        
        # Generate value_rules.yaml for current table
        generate_value_rules_yaml(base_dir, args.object, args.variant, df)
        
        print("\nAll YAML files generated successfully!")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def generate_column_map_yaml(object_name, variant, source_fields, target_fields, excel_source_path):
    """Generate the complete column_map.yaml content with advanced matching."""
    
    # Generate timestamp
    timestamp = datetime.now().strftime("%Y%m%d %H%M")
    
    # Create advanced mapping with detailed results
    fuzzy_config = FuzzyConfig(
        threshold=0.6,
        max_suggestions=3,
        levenshtein_weight=0.5,
        jaro_winkler_weight=0.5
    )
    
    mapping_lines, exact_matches, fuzzy_matches, unmapped_sources = create_advanced_column_mapping(
        source_fields, target_fields, fuzzy_config
    )
    
    # Generate the YAML content
    yaml_content = []
    yaml_content.append(f"# generated by transform-myd-minimal advanced map @ {timestamp}")
    yaml_content.append(f"# source: {excel_source_path}")
    yaml_content.append("# Advanced field matching with exact, synonym, and fuzzy algorithms")
    yaml_content.append("")
    yaml_content.append("## Match fields")
    yaml_content.append("")
    
    # Add all mappings
    for line in mapping_lines:
        yaml_content.append(line)
    
    yaml_content.append("")
    yaml_content.append("")
    yaml_content.append(f"# column_map.yaml – {variant.upper()} datamap (source → target) + descriptions")
    yaml_content.append(f"# object: {variant.upper()}")
    yaml_content.append("# version: 2 (Advanced Matching)")
    
    # Add detailed mapping comments with advanced match information
    yaml_content.append("# mappings:")
    
    # Process exact matches
    for result in exact_matches:
        yaml_content.extend([
            f"#  - source: {result.source_field}",
            f"#    source_description: \"{result.source_description}\"",
            f"#    target: {result.target_field}",
            f"#    target_description: \"{result.target_description}\"",
            f"#    decision: AUTO_MAP",
            f"#    confidence: {result.confidence_score:.2f}",
            f"#    match_type: {result.match_type}",
            f"#    rule: copy",
            f"#    reason: \"{result.reason}\"",
            "#"
        ])
    
    # Process fuzzy/synonym matches
    for result in fuzzy_matches:
        yaml_content.extend([
            f"#  - source: {result.source_field}",
            f"#    source_description: \"{result.source_description}\"",
            f"#    target: {result.target_field}",
            f"#    target_description: \"{result.target_description}\"",
            f"#    decision: AUTO_MAP",
            f"#    confidence: {result.confidence_score:.2f}",
            f"#    match_type: {result.match_type}",
            f"#    algorithm: {result.algorithm or 'N/A'}",
            f"#    rule: copy",
            f"#    reason: \"{result.reason}\"",
            "#"
        ])
    
    # Add derived targets section with smart logic
    yaml_content.append("#derived_targets:")
    mapped_targets = {result.target_field for result in exact_matches + fuzzy_matches if result.target_field}
    
    for _, target_row in target_fields.iterrows():
        target_name = target_row['field_name']
        if target_name not in mapped_targets:
            target_desc = target_row['field_description']
            
            # Use smart logic to determine if this should be a constant field
            if is_constant_field(target_name, target_desc):
                # This appears to be an operational flag or control field
                yaml_content.extend([
                    f"#  - target: {target_name}",
                    f"#    target_description: \"{target_desc}\"",
                    f"#    decision: DERIVED",
                    f"#    confidence: 0.90",
                    f"#    match_type: constant_detection",
                    f"#    rule: constant     # kies 'X' om overschrijven te blokkeren, of ' ' (blank) anders",
                    f"#    value: \" \"",
                    f"#    reason: \"Operationele flag; geen semantische bron in source\"",
                    "#"
                ])
            else:
                # This appears to be a regular derived field that needs business logic
                yaml_content.extend([
                    f"#  - target: {target_name}",
                    f"#    target_description: \"{target_desc}\"",
                    f"#    decision: DERIVED",
                    f"#    confidence: 0.80",
                    f"#    match_type: business_logic_required",
                    f"#    rule: derive       # implementeer business logica voor dit veld",
                    f"#    reason: \"Afgeleid veld; vereist business logica implementatie\"",
                    "#"
                ])
    
    # Add unmapped sources section with advanced information
    yaml_content.append("#unmapped_sources:")
    for result in unmapped_sources:
        yaml_content.extend([
            f"#  - source: {result.source_field}",
            f"#    source_description: \"{result.source_description}\"",
            f"#    decision: UNMAPPED",
            f"#    confidence: {result.confidence_score:.2f}",
            f"#    match_type: {result.match_type}",
            f"#    reason: \"{result.reason}\"",
            "#"
        ])
    
    # Add advanced matching statistics
    yaml_content.append("#matching_statistics:")
    yaml_content.append(f"#  total_sources: {len(source_fields)}")
    yaml_content.append(f"#  total_targets: {len(target_fields)}")
    yaml_content.append(f"#  exact_matches: {len(exact_matches)}")
    yaml_content.append(f"#  fuzzy_matches: {len(fuzzy_matches)}")
    yaml_content.append(f"#  unmapped_sources: {len(unmapped_sources)}")
    yaml_content.append(f"#  mapping_coverage: {((len(exact_matches) + len(fuzzy_matches)) / len(source_fields) * 100):.1f}%")
    yaml_content.append("#")
    
    return '\n'.join(yaml_content)


def main():
    # Check if this is the old format (no subcommand)
    if len(sys.argv) > 1 and not sys.argv[1] in ['map', '-h', '--help']:
        # Old format detected, handle backward compatibility
        print("Note: Using legacy format. Consider using 'map' subcommand: python3 transform_myd_minimal.py map -object {} -variant {}".format(
            sys.argv[sys.argv.index('-object') + 1] if '-object' in sys.argv else 'OBJECT',
            sys.argv[sys.argv.index('-variant') + 1] if '-variant' in sys.argv else 'VARIANT'
        ))
        
        # Parse with old format
        old_parser = argparse.ArgumentParser(description='Generate column mapping YAML from Excel field definitions (Advanced Version)')
        old_parser.add_argument('-object', '--object', required=True, help='Object name (e.g., m140)')
        old_parser.add_argument('-variant', '--variant', required=True, help='Variant name (e.g., bnka)')
        old_parser.add_argument('--fuzzy-threshold', type=float, default=0.6, help='Fuzzy matching threshold (0.0-1.0)')
        old_parser.add_argument('--max-suggestions', type=int, default=3, help='Maximum fuzzy match suggestions')
        old_parser.add_argument('--disable-fuzzy', action='store_true', help='Disable fuzzy matching')
        
        args = old_parser.parse_args()
        run_map_command(args)
        return
    
    # New format with subcommands
    parser = argparse.ArgumentParser(description='Transform MYD Minimal - Advanced Field Matching and YAML Generation')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Map subcommand (default behavior)
    map_parser = subparsers.add_parser('map', help='Generate column mapping and YAML files')
    map_parser.add_argument('-object', '--object', required=True, help='Object name (e.g., m140)')
    map_parser.add_argument('-variant', '--variant', required=True, help='Variant name (e.g., bnka)')
    map_parser.add_argument('--fuzzy-threshold', type=float, default=0.6, help='Fuzzy matching threshold (0.0-1.0)')
    map_parser.add_argument('--max-suggestions', type=int, default=3, help='Maximum fuzzy match suggestions')
    map_parser.add_argument('--disable-fuzzy', action='store_true', help='Disable fuzzy matching')
    
    # Parse arguments
    args = parser.parse_args()
    
    # If no command is specified, show help
    if args.command is None:
        parser.print_help()
        sys.exit(1)
    
    # Execute the appropriate command
    if args.command == 'map':
        run_map_command(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()