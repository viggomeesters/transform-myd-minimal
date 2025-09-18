# Transform MYD Minimal - Advanced Field Matching

CLI tool voor het genereren van column mapping YAML bestanden uit Excel field definities.

**Nu met geavanceerde field matching algoritmen!**

## Features

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

## Gebruik

```bash
./transform-myd-minimal -object <object_name> -variant <variant_name> [OPTIONS]
```

### Basis Voorbeeld

```bash
./transform-myd-minimal -object m140 -variant bnka
```

### Geavanceerde Opties

```bash
# Met aangepaste fuzzy threshold
./transform-myd-minimal -object m140 -variant bnka --fuzzy-threshold 0.8

# Fuzzy matching uitschakelen
./transform-myd-minimal -object m140 -variant bnka --disable-fuzzy

# Maximum suggesties aanpassen
./transform-myd-minimal -object m140 -variant bnka --max-suggestions 5
```

## Command Line Opties

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
Fuzzy/Synonym matches: 1
Unmapped sources: 25
Mapping coverage: 32.4%

Fuzzy/Synonym matches found:
  IBAN_RULE → BANKL (fuzzy, confidence: 0.60)
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

### 📊 Matching Statistics
Elk run toont:
- Totaal aantal source/target velden
- Aantal exact/fuzzy/unmapped matches
- Mapping coverage percentage
- Details van fuzzy matches met confidence scores

Dit commando:
1. Leest het bestand `02_fields/fields_{object}_{variant}.xlsx`
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
- `02_fields/fields_{object}_{variant}.xlsx` - Input Excel bestand
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