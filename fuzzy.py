#!/usr/bin/env python3
"""
Fuzzy matching algorithms and field normalization for transform-myd-minimal.

Contains all logic and algorithms for fuzzy matching including:
- Levenshtein distance calculation
- Jaro-Winkler similarity
- Field normalization
- Threshold handling
"""

import re
import unicodedata
from dataclasses import dataclass
from typing import Optional


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