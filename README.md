# Transform MYD Minimal - Integrated YAML Workflow

CLI tool voor het genereren van column mapping en YAML bestanden uit Excel field definities.

**Nu met geïntegreerde YAML workflow en geavanceerde field matching algoritmen!**

## Features

### 🔄 Integrated YAML Workflow (v3.0)
- **Single command** genereert alle benodigde YAML bestanden
- **Automatische generatie** van fields.yaml, value_rules.yaml, object_list.yaml
- **Geïntegreerde workflow** zonder aparte scripts
- **Backward compatibility** met legacy command format

### 🚀 Advanced Field Matching System
- **Exact matching** op genormaliseerde veldnamen en beschrijvingen
- **Synonym matching** met uitbreidbare NL/EN synonym lijst
- **Fuzzy matching** met Levenshtein en Jaro-Winkler algoritmen
- **Configureerbare thresholds** en top-N suggesties
- **Confidence scores**: "exact", "synoniem", "fuzzy", "geen match"

### 🧠 Smart Transformation Logic
- Intelligente detectie van operational flags vs. business logic velden
- Automatische toewijzing van `rule: constant` voor operationele velden
- `rule: derive` voor velden die business logica vereisen

### 📋 Central Mapping Memory System
- **Centraal geheugenbestand** (`central_mapping_memory.yaml`) voor herbruikbare mapping regels
- **Skip rules** - velden uitsluiten van mapping met auditeerbare comments
- **Manual mappings** - handmatige veld-naar-veld mappings met business context
- **Global + table-specific overrides** - flexibele regel hiërarchie
- **Comments** worden bewaard in output voor transparante overdracht tussen collega's
- **Prioriteit**: Central memory regels worden eerst toegepast, daarna automatische matching

## Gebruik

### Nieuwe format (aanbevolen)
```bash
python3 transform_myd_minimal.py map -object <object_name> -variant <variant_name> [OPTIONS]
```

### Legacy format (backward compatible)
```bash
python3 transform_myd_minimal.py -object <object_name> -variant <variant_name> [OPTIONS]
```

### Basis Voorbeeld

```bash
# Nieuwe format
python3 transform_myd_minimal.py map -object m140 -variant bnka

# Legacy format (toont waarschuwing)
python3 transform_myd_minimal.py -object m140 -variant bnka
```

### Geavanceerde Opties

```bash
# Met aangepaste fuzzy threshold
python3 transform_myd_minimal.py map -object m140 -variant bnka --fuzzy-threshold 0.8

# Fuzzy matching uitschakelen
python3 transform_myd_minimal.py map -object m140 -variant bnka --disable-fuzzy

# Maximum suggesties aanpassen
python3 transform_myd_minimal.py map -object m140 -variant bnka --max-suggestions 5
```

## Command Line Opties

| Option | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| `map` | subcommand | Nee* | - | Genereer column mapping en YAML files |
| `-object OBJECT` | string | **Ja** | - | Object naam (bijv. m140) |
| `-variant VARIANT` | string | **Ja** | - | Variant naam (bijv. bnka) |
| `--fuzzy-threshold` | float | Nee | 0.6 | Fuzzy matching threshold (0.0-1.0) |
| `--max-suggestions` | int | Nee | 3 | Maximum fuzzy match suggesties |
| `--disable-fuzzy` | flag | Nee | False | Fuzzy matching uitschakelen |

*Het `map` subcommand is optioneel voor backward compatibility

Voor een volledig overzicht van alle CLI opties, zie: **[CLI_OPTIONS.md](CLI_OPTIONS.md)**

### Snelle Referentie

- `--fuzzy-threshold FLOAT`: Fuzzy matching threshold (0.0-1.0, default: 0.6)
- `--max-suggestions INT`: Maximum aantal fuzzy match suggesties (default: 3)
- `--disable-fuzzy`: Schakel fuzzy matching uit

## Uitvoer

Het script genereert nu:
1. **Mapping coverage statistieken** in de console
2. **Geavanceerde match informatie** in de YAML output
3. **Algoritme details** voor fuzzy matches
4. **Confidence scores** voor alle matches

### Voorbeeld Console Output
```
=== Advanced Matching Results ===
Exact matches: 11
Fuzzy/Synonym matches: 0
Unmapped sources: 26
Audit matches (fuzzy to exact-mapped targets): 1
Mapping coverage: 29.7%

Audit matches found (fuzzy matches to exact-mapped targets):
  IBAN_RULE → BANKL (audit, confidence: 0.60)
```

## Algoritme Details

### 🎯 Exact Matching
- Normaliseert veldnamen (accenten weg, lowercase, geen speciale tekens)
- 100% confidence bij exacte naam + beschrijving match
- 95% confidence bij exacte naam match

### 🔄 Synonym Matching
- Uitbreidbare woordenlijst voor NL/EN termen
- Ondersteunt business termen (klant/customer, naam/name)
- Banking specifieke termen (bank, rekening/account, saldo/balance)
- Technische termen (sleutel/key, waarde/value)
- 85% confidence voor synonym matches

### 🔍 Fuzzy Matching
- **Levenshtein distance**: Edit distance algoritme
- **Jaro-Winkler similarity**: Optimaal voor naam vergelijking
- Configureerbare algoritme weights (default: 50/50)
- Gecombineerde score: 70% veldnaam + 30% beschrijving
- Instelbare threshold (default: 0.6)

### 🚫 Duplicate Target Prevention
Het script implementeert een geavanceerde twee-fase matching strategie om te voorkomen dat een target veld (bijv. BANKL) meerdere keren wordt toegewezen:

**Fase 1: Exact Matching**
- Eerst worden alle exacte matches geïdentificeerd
- Deze target velden worden gemarkeerd als "bezet"

**Fase 2: Fuzzy Matching**
- Fuzzy matching wordt alleen uitgevoerd voor nog niet toegewezen target velden
- Dit voorkomt dat BANKL zowel exact als fuzzy gemapt wordt

**Audit Logging**
- Fuzzy matches naar reeds exact-gemapte targets worden alsnog geregistreerd als audit commentaren
- Deze verschijnen in de YAML output als `# AUDIT: source -> target` 
- Voorbeeld: Als IBAN_RULE fuzzy zou matchen met BANKL (die al exact gemapt is), wordt dit gelogd voor auditdoeleinden
- Audit matches tellen niet mee voor coverage percentage

### 📊 Matching Statistics
Elk run toont:
- Totaal aantal source/target velden
- Aantal exact/fuzzy/unmapped matches
- Aantal audit matches (fuzzy matches naar exact-gemapte targets)
- Mapping coverage percentage (exclusief audit matches)
- Details van fuzzy matches met confidence scores
- Details van audit matches voor transparency

Dit commando:
1. Leest het bestand `data/02_fields/fields_{object}_{variant}.xlsx`
2. Past geavanceerde matching algoritmen toe
3. Genereert `config/{object}/{variant}/column_map.yaml` met uitgebreide metadata

## Vereisten

- Python 3.x
- pandas
- openpyxl
- pyyaml

## Installatie vereisten

```bash
pip install pandas openpyxl pyyaml
```

## Bestandsstructuur

Het script verwacht de volgende structuur:
- `data/02_fields/fields_{object}_{variant}.xlsx` - Input Excel bestand
- `config/{object}/{variant}/column_map.yaml` - Output YAML bestand (wordt gegenereerd)

## Help

```bash
./transform-myd-minimal --help
```

**Uitgebreide CLI documentatie**: Zie [CLI_OPTIONS.md](CLI_OPTIONS.md) voor alle opties, voorbeelden en changelog.

## Smart Transformation Logic

Het script gebruikt intelligente logica voor het toekennen van mapping regels aan derived targets:

### Constant Fields
Velden worden automatisch gemarkeerd als `rule: constant` wanneer ze operationele flags of controle velden lijken te zijn, gebaseerd op:

**Field name patterns:**
- overwrite, flag, control, indicator, switch, enable, disable, active, status

**Description patterns:**
- overwrite, flag, operational, control, indicator, do not, block, prevent, enable, disable, switch, toggle, status

**Voorbeeld:**
- `ISNOTOVERWRITE` met beschrijving "Do Not Overwrite Existing Data" → `rule: constant`

### Derived Fields
Velden die niet als constant worden herkend krijgen `rule: derive` en vereisen business logica implementatie.

**Voorbeeld:**
- `CUSTOMER_TOTAL` met beschrijving "Total amount for customer" → `rule: derive`

## Central Mapping Memory System

Het central mapping memory systeem maakt gebruik van een centraal configuratiebestand (`central_mapping_memory.yaml`) in de project root voor herbruikbare mapping regels.

### 📋 Configuratie Structuur

Het `central_mapping_memory.yaml` bestand ondersteunt:

1. **Global skip fields** - Skip regels die op alle tabellen van toepassing zijn
2. **Global manual mappings** - Handmatige mappings die op alle tabellen van toepassing zijn  
3. **Table-specific overrides** - Tabelspecifieke regels die global regels overschrijven

### 🚫 Skip Rules

Skip rules zorgen ervoor dat bepaalde source velden worden uitgesloten van mapping:

```yaml
global_skip_fields:
  - source_field: "ZRES1"
    source_description: "Reserved field 1" 
    skip: true
    comment: "Reserved field not used in current implementation"

table_specific:
  m140_bnka:
    skip_fields:
      - source_field: "TEMP_FIELD"
        source_description: "Temporary processing field"
        skip: true
        comment: "BNKA specific: Field only used during ETL processing"
```

### 🎯 Manual Mappings

Manual mappings definiëren expliciete veld-naar-veld toewijzingen:

```yaml
global_manual_mappings:
  - source_field: "IBAN_RULE"
    source_description: "IBAN Validation Rule"
    target: "SWIFT"
    target_description: "SWIFT Code for international transfers"
    comment: "Business rule: Map IBAN validation to SWIFT for process alignment"

table_specific:
  m140_bnka:
    manual_mappings:
      - source_field: "ERNAM"
        source_description: "Name of Person who Created the Object"
        target: "BANKL"
        target_description: "Bank Key"
        comment: "BNKA specific: Creator field mapped to bank key for audit trail"
```

### 🔄 Verwerkingsvolgorde

1. **Central memory skip rules** - Velden worden uitgesloten van verdere verwerking
2. **Central memory manual mappings** - Expliciete mappings worden toegepast
3. **Automatische matching algoritmen** - Voor overige velden (exact, synonym, fuzzy)

### 📊 Output & Auditability

Het systeem toont welke central memory regels zijn toegepast:

**Console output:**
```
Central memory skip rules applied: 2
Central memory manual mappings applied: 2

Central memory skip rules applied:
  SKIP: ZRES1 - Central memory skip rule: Reserved field not used
  SKIP: ZRES2 - Central memory skip rule: Reserved field not used

Central memory manual mappings applied:
  MANUAL: IBAN_RULE → SWIFT - Business rule mapping for process alignment
  MANUAL: ERNAM → BANKL - Creator mapped to bank key for audit trail
```

**YAML output bevat gedetailleerde comments:**
```yaml
# Central Memory Skip Rules Applied:
# SKIP: ZRES1
#   source_description: "Residue"
#   skip_reason: "Central memory skip rule: Reserved field not used"
#   confidence: 1.00
#   rule_type: central_skip

# Central Memory Manual Mappings Applied:
#  - source: IBAN_RULE
#    source_description: "IBAN Rule"
#    target: SWIFT
#    target_description: "SWIFT Code for international transfers"
#    decision: MANUAL_MAP
#    confidence: 1.00
#    match_type: central_manual
#    rule: copy
#    reason: "Business rule mapping for process alignment"
```

## Geïntegreerde YAML Generator

De YAML generatie functionaliteit is nu geïntegreerd in het hoofdscript. Bij elke `map` opdracht worden automatisch alle benodigde YAML-bestanden gegenereerd:

**Automatisch gegenereerde bestanden:**
1. **object_list.yaml** - Overzicht van alle objecten en hun tables uit `config/{object}/{variant}`
2. **fields.yaml** per table - Uitgebreide veldinfo (name, description, type, required, key) uit Excel-bestanden  
3. **value_rules.yaml** per table - Automatische rules voor mandatory/operational/derived velden
4. **column_map.yaml** per table - Geavanceerde field mapping met fuzzy matching

**Gebruik:**
```bash
# Genereert alle YAML files automatisch
python3 transform_myd_minimal.py map -object m140 -variant bnka
```

**Gegenereerde bestanden:**
- `config/object_list.yaml` - Master overzicht (updated bij elke run)
- `config/{object}/{variant}/fields.yaml` - Per table velddefinities
- `config/{object}/{variant}/value_rules.yaml` - Per table value rules
- `config/{object}/{variant}/column_map.yaml` - Per table column mapping

**Rule types:**
- `required` - Voor mandatory velden (field_is_mandatory=True)
- `constant` - Voor operationele velden (automatisch gedetecteerd)
- `derive` - Voor berekende velden (automatisch gedetecteerd)  
- `map` - Voor directe mapping velden

Het script scant automatisch de bestaande mappenstructuur en Excel-bestanden in `data/02_fields/fields_{object}_{variant}.xlsx`.

## Versie Informatie

**Huidige versie: 3.0.0 - Integrated Workflow**

```bash
# Bekijk versie informatie
python3 transform_myd_minimal.py --version
```

### Versie Geschiedenis
- **v3.0** - Geïntegreerde YAML workflow met `map` subcommand
- **v2.0** - Advanced matching algoritmen (fuzzy, synonym)
- **v1.0** - Basis exact matching functionaliteit

Voor volledige documentatie zie [CLI_OPTIONS.md](CLI_OPTIONS.md)