# Multi-File YAML Schema Documentation
# This document defines the structure and schema for the new migrations/ directory approach

## Overview

The new multi-file YAML structure addresses the pain points of the previous single-file approach by:
- Clear separation of concerns (fields, mappings, validation, transformations)
- Non-redundant structure with SAP object as anchor
- Auditable mapping decisions with clear acceptance/rejection tracking
- Table-scoped (not object-wide) value rules and transformations

## Directory Structure

```
migrations/
├── objects.yaml                           # Catalog of all migration objects
├── {OBJECT_CODE}/                         # One directory per business object (M120, M140, etc.)
│   └── {table_name}/                      # One directory per SAP table variant
│       ├── fields.yaml                    # Target field definitions
│       ├── mappings.yaml                  # Source-to-target field mappings
│       ├── validation.yaml                # Validation rules and constraints
│       └── transformations.yaml           # Value transformation logic
```

## File Schemas

### objects.yaml (Catalog File)
```yaml
objects:
  - object_code: "M120"                    # Business object identifier
    object_description: "Profit Centers"   # Human-readable description
    sap_object_anchor: "CEPC"             # Primary SAP object being populated
    tables:                               # List of table variants for this object
      - "cepc"                           # Main table
      - "cepct"                          # Text table
```

### fields.yaml (Target Field Definitions)
```yaml
metadata:
  object_code: "M120"                     # Links back to object catalog
  table_name: "cepc"                     # SAP table name
  sap_table: "CEPC"                      # Official SAP table identifier
  description: "Profit Center Master"     # Business description
  last_updated: "2024-01-18"             # Maintenance timestamp

fields:
  - name: "MANDT"                         # SAP field name
    description: "Client"                 # SAP field description
    data_type: "CLNT"                     # SAP data type
    length: 3                            # Field length
    required: true                       # Mandatory field flag
    key_field: true                      # Part of primary key
    business_key: false                  # Business key flag

field_groups:                            # Logical groupings for navigation
  keys:
    description: "Primary key fields"
    fields: ["MANDT", "PRCTR", "DATBI"]
```

### mappings.yaml (Source-to-Target Mappings)
```yaml
metadata:
  object_code: "M120"
  table_name: "cepc"
  source_system: "Legacy ERP"
  mapping_version: "1.0"
  last_updated: "2024-01-18"

direct_mappings:                          # 1:1 field mappings
  - source_field: "CLIENT_ID"
    source_description: "Client identifier"
    target_field: "MANDT"
    target_description: "Client"
    mapping_type: "direct"
    confidence: 1.0
    comments: "Standard client mapping"

derived_mappings:                         # Fields requiring business logic
  - target_field: "BUKRS"
    target_description: "Company Code"
    derivation_logic: "lookup_company_code"
    source_fields: ["PROFIT_CENTER_CODE", "DIVISION"]
    comments: "Derive company code from profit center"

central_memory_mappings:                  # From central_mapping_memory.yaml
  - source_field: "IBAN_RULE"
    target_field: "SWIFT"
    mapping_type: "central_memory"
    confidence: 1.0
    comments: "Business rule mapping"

skip_rules:                              # Fields intentionally not mapped
  - source_field: "ZRES1"
    skip_reason: "Reserved field not used"
    confidence: 1.0

unmapped_sources:                        # Fields with no target (audit)
  - source_field: "LEGACY_ID"
    skip_reason: "Internal system field"

mapping_stats:                           # Coverage metrics
  total_source_fields: 8
  mapped_source_fields: 6
  coverage_percentage: 75.0
```

### validation.yaml (Data Quality Rules)
```yaml
metadata:
  object_code: "M120"
  table_name: "cepc"
  validation_version: "1.0"
  last_updated: "2024-01-18"

field_validations:                       # Individual field rules
  MANDT:
    - rule_type: "required"
      description: "Client must be provided"
      error_level: "critical"
    - rule_type: "length"
      min_length: 3
      max_length: 3
      error_level: "critical"

cross_field_validations:                 # Multi-field rules
  - rule_name: "date_range_validity"
    description: "Valid From <= Valid To"
    fields: ["DATAB", "DATBI"]
    rule_logic: "DATAB <= DATBI"
    error_level: "critical"

business_rules:                          # Business logic validation
  - rule_name: "profit_center_uniqueness"
    description: "PC unique within controlling area"
    scope: "table"
    fields: ["PRCTR", "KOKRS", "DATAB", "DATBI"]
    error_level: "critical"

audit_rules:                            # Audit and acceptance criteria
  - rule_name: "source_traceability"
    requirement: "Maintain source system reference"
    acceptance_criteria: "100% traceability"
```

### transformations.yaml (Value Transformation Logic)
```yaml
metadata:
  object_code: "M120"
  table_name: "cepc"
  transformation_version: "1.0"
  last_updated: "2024-01-18"

field_transformations:                   # Field-specific transformations
  MANDT:
    transformation_type: "constant"
    target_value: "100"
    description: "Set client to production"
    business_rule: "All data goes to client 100"
    
  PRCTR:
    transformation_type: "format"
    source_format: "legacy_pc_code"
    target_format: "sap_pc_code"
    rules:
      - if_source_length: 6
        then: "left_pad_zeros_to_10"
    examples:
      - source: "pc001"
        target: "0000000001"

conditional_transformations:             # Complex business logic
  - condition_name: "historical_profit_centers"
    conditions:
      - field: "LEGACY_STATUS"
        operator: "equals"
        value: "HISTORICAL"
    transformations:
      DATBI:
        override_value: "20231231"
        reason: "Close historical PCs"

value_mappings:                          # Lookup tables
  legacy_status_to_sap:
    "ACTIVE": "A"
    "INACTIVE": "I"

audit_requirements:                      # Transformation audit
  - track_field: "all"
    requirement: "Log original and transformed values"
    retention_period: "7_years"
```

## Key Design Principles

1. **SAP Object Anchor**: Each migration object is anchored to a SAP business object, with tables as variants
2. **Clear Separation**: Each file has a single responsibility (fields, mappings, validation, transformations)
3. **Non-Redundant**: Information appears in only one place; no duplication between files
4. **Table-Scoped**: Value rules and transformations are scoped to specific tables, not applied object-wide
5. **Auditable**: Every mapping decision is tracked with reasons and confidence levels
6. **Acceptance Tracking**: Clear distinction between accepted mappings and rejected fields with reasons

## Migration Benefits

- **Clarity**: Each file has a clear purpose and scope
- **Maintainability**: Changes to one aspect don't affect others
- **Auditability**: Full traceability of mapping decisions
- **Scalability**: Easy to add new objects and tables
- **Business Alignment**: Structure reflects SAP business objects and processes