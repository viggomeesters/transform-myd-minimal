# Mapping User Experience - Usage Guide

## Overview

Deze gids beschrijft hoe je de mapping user experience features van transform-myd-minimal gebruikt.

## 1. Excel Mapping Editor Template

### Locatie
`migrations/mapping_editor_template.xlsx`

### Gebruik

1. **Open het template**
   ```bash
   # Open het bestand in Excel of LibreOffice
   open migrations/mapping_editor_template.xlsx  # macOS
   xdg-open migrations/mapping_editor_template.xlsx  # Linux
   start migrations/mapping_editor_template.xlsx  # Windows
   ```

2. **Vul de mapping gegevens in**
   - **Source Field**: Naam van het bronveld
   - **Target Field**: Naam van het doelveld
   - **Transformation**: Type transformatie (gebruik dropdown)
     - `copy`: Directe kopie van waarde
     - `constant`: Vaste waarde voor alle records
     - `derive`: Afgeleide waarde (business logica vereist)
     - `lookup`: Opzoeken in mapping tabel
     - `concatenate`: Samenvoegen van meerdere waarden
     - `split`: Splitsen van waarde
     - `transform`: Aangepaste transformatie
   - **Note**: Optionele notities of opmerkingen

3. **Validatie**
   - Lege verplichte velden worden automatisch rood gemarkeerd
   - Gebruik de dropdowns voor consistente waarden

### Voorbeeld

| Source Field | Target Field | Transformation | Note |
|--------------|--------------|----------------|------|
| BANK_NAME | BANKL | copy | Direct kopiëren |
| COUNTRY_CODE | LAND1 | lookup | Land code → land naam |
| - | BUKRS | constant | Vaste waarde: 1000 |

## 2. Web-Based Mapping Editor

### Installatie

```bash
pip install streamlit
```

### Starten

```bash
streamlit run scripts/mapping_editor_webui.py
```

De web-UI opent automatisch in je browser op `http://localhost:8501`

### Functies

#### Upload Bestand
1. Klik op "Browse files" in het upload gebied
2. Selecteer een Excel (.xlsx) of YAML (.yml/.yaml) bestand
3. Het bestand wordt automatisch geladen en getoond

#### Mappings Bewerken
1. Klik in een cel om de waarde te wijzigen
2. Gebruik de dropdown voor Transformation types
3. Klik op "➕ Add Row" om een nieuwe rij toe te voegen
4. Klik op "🗑️ Remove Empty Rows" om lege rijen te verwijderen

#### Valideren
1. Klik op "🔍 Validate" knop
2. Bekijk fouten (rood) en waarschuwingen (geel)
3. Pas mappings aan op basis van feedback

#### Exporteren
1. Klik op "📥 Download as Excel" voor Excel export
2. Klik op "📥 Download as YAML" voor YAML export
3. Het bestand wordt gedownload naar je Downloads folder

### Screenshots

**Upload & Edit:**
![Web UI Upload](docs/images/webui-upload.png)

**Validation:**
![Web UI Validation](docs/images/webui-validation.png)

## 3. Auto-Suggest Mapping

### Gebruik

```bash
# Basis gebruik
python scripts/auto_suggest_mapping.py \
  --object m140 \
  --variant bnka

# Met aangepaste instellingen
python scripts/auto_suggest_mapping.py \
  --object m140 \
  --variant bnka \
  --fuzzy-threshold 0.6 \
  --max-suggestions 3

# Output naar bestand
python scripts/auto_suggest_mapping.py \
  --object m140 \
  --variant bnka \
  --output suggestions.yaml
```

### Parameters

- `--object`: Object naam (verplicht)
- `--variant`: Variant naam (verplicht)
- `--root`: Root directory van het project (default: huidige directory)
- `--fuzzy-threshold`: Minimum similarity score (0.0-1.0, default: 0.6)
- `--max-suggestions`: Maximum aantal suggesties per veld (default: 3)
- `--output`: Output bestand voor suggesties (optioneel)

### Voorbeeld Output

```
Source: BANKS (string)
  1. BANKS - Confidence: 79.7%
     Reason: High name similarity (100.0%); Compatible data types
  2. BANKL - Confidence: 78.0%
     Reason: High name similarity (86.0%); Description match (68.0%); Compatible data types

Source: BANKA (string)
  1. BANKL - Confidence: 78.0%
     Reason: High name similarity (86.0%); Description match (68.0%); Compatible data types
  2. BANKA - Confidence: 77.6%
     Reason: High name similarity (100.0%); Compatible data types
```

### Hoe het Werkt

1. **Fuzzy Matching**: Gebruikt Levenshtein en Jaro-Winkler algoritmen
2. **Data Type Match**: Controleert compatibiliteit van data types
3. **Sample Values**: Analyseert sample waarden voor patronen
4. **Combined Score**: Gewogen combinatie van alle factoren
   - Naam similarity: 40%
   - Beschrijving similarity: 20%
   - Data type match: 20%
   - Sample values: 20%

## 4. Test-Driven Mapping

### Test Cases Definiëren

Maak een YAML bestand met test cases:

```yaml
# tests/my_mapping_tests.yaml
test_cases:
  - name: test_bank_name_copy
    source_field: BANK_NAME
    target_field: BANKL
    source_value: "Deutsche Bank"
    expected_value: "Deutsche Bank"
    transformation: copy
    description: "Copy bank name directly"

  - name: test_country_constant
    source_field: ANY_FIELD
    target_field: BUKRS
    source_value: "ignored"
    expected_value: "1000"
    transformation: constant
    description: "Set constant company code"
```

### Tests Uitvoeren

#### Via pytest (Unit Tests)

```bash
pytest tests/test_mapping.py -v
```

#### Via Command-Line (YAML Test Cases)

```bash
# Basis gebruik
python tests/test_mapping.py --test-file tests/sample_mapping_testcases.yaml

# Met HTML rapport
python tests/test_mapping.py \
  --test-file tests/sample_mapping_testcases.yaml \
  --html-report test_results.html

# Met JSON output
python tests/test_mapping.py \
  --test-file tests/sample_mapping_testcases.yaml \
  --output results.json
```

### HTML Rapport

Het HTML rapport toont:
- **Summary**: Totaal, passed, failed counts
- **Details**: Per test case
  - Source field en waarde
  - Target field
  - Transformation type
  - Expected vs Actual waarden
  - Status (PASS/FAIL)

### CI/CD Integratie

Voeg toe aan je GitHub Actions workflow:

```yaml
- name: Run mapping tests
  run: |
    pytest tests/test_mapping.py -v
    python tests/test_mapping.py --test-file tests/sample_mapping_testcases.yaml --html-report test-results.html
```

## 5. Workflow Voorbeeld

### Complete Mapping Workflow

1. **Genereer auto-suggesties**
   ```bash
   python scripts/auto_suggest_mapping.py \
     --object m140 \
     --variant bnka \
     --output suggestions.yaml
   ```

2. **Review suggesties in web-UI**
   ```bash
   streamlit run scripts/mapping_editor_webui.py
   # Upload suggestions.yaml
   # Bewerk en valideer mappings
   # Download als mapping.xlsx
   ```

3. **Definieer test cases**
   - Maak `tests/m140_bnka_tests.yaml`
   - Voeg test cases toe voor belangrijke mappings

4. **Run tests**
   ```bash
   python tests/test_mapping.py \
     --test-file tests/m140_bnka_tests.yaml \
     --html-report test_results.html
   ```

5. **Itereer tot alle tests slagen**
   - Pas mappings aan op basis van test failures
   - Run tests opnieuw
   - Herhaal tot 100% pass rate

## Tips & Best Practices

### Excel Template
- Gebruik conditional formatting om fouten snel te zien
- Kopieer het template voor elk object/variant
- Bewaar templates in version control

### Web-UI
- Valideer regelmatig tijdens het bewerken
- Exporteer naar YAML voor version control
- Gebruik Excel export voor stakeholder reviews

### Auto-Suggest
- Start met lagere threshold (0.5) voor meer suggesties
- Review hoge confidence matches (>80%) eerst
- Gebruik suggesties als startpunt, niet als finale mapping

### Test-Driven
- Begin met simpele copy transformations
- Voeg geleidelijk complexere tests toe
- Test edge cases (null, empty, special characters)
- Integreer in CI/CD pipeline

## Troubleshooting

### Web-UI start niet
```bash
# Controleer of Streamlit is geïnstalleerd
pip install streamlit

# Controleer of poort 8501 beschikbaar is
lsof -i :8501
```

### Auto-suggest geeft geen suggesties
- Controleer of index_source.yaml en index_target.yaml bestaan
- Verlaag fuzzy-threshold (bijv. naar 0.4)
- Controleer of velden data types hebben

### Tests falen
- Controleer of transformatie configuratie correct is
- Test eerst met simpele copy transformations
- Bekijk HTML rapport voor details van failures

## Support

Voor vragen of problemen:
- Check README.md voor algemene documentatie
- Check docs/DEVELOPMENT.md voor development details
- Open een issue in de GitHub repository
