#!/usr/bin/env python3
"""
Synonym matching logic and dictionaries for transform-myd-minimal.

Contains all logic and dictionary for synonym matching including:
- NL/EN business terms
- Banking specific terms
- Technical terms
- Synonym lookup and matching algorithms
"""

from typing import List
from .fuzzy import FieldNormalizer


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
        "configuratie": ["configuration", "konfiguration"],
    }

    @classmethod
    def find_synonyms(cls, term: str) -> List[str]:
        """Find synonyms for a given term."""
        term_normalized = FieldNormalizer.normalize_field_name(term)
        synonyms = []

        for key, values in cls.SYNONYMS.items():
            key_normalized = FieldNormalizer.normalize_field_name(key)
            if term_normalized == key_normalized:
                synonyms.extend(
                    [FieldNormalizer.normalize_field_name(v) for v in values]
                )
                break

            for value in values:
                value_normalized = FieldNormalizer.normalize_field_name(value)
                if term_normalized == value_normalized:
                    synonyms.append(key_normalized)
                    synonyms.extend(
                        [
                            FieldNormalizer.normalize_field_name(v)
                            for v in values
                            if v != value
                        ]
                    )
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
