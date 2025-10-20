# Transform MYD Minimal - Step-by-Step Object+Variant Pipeline

CLI tool voor het genereren van column mapping en YAML bestanden met een stapsgewijze Object+Variant pipeline. Alle input en output wordt per **object** en **variant** geadministreerd, zonder globale output-bestanden.

---

## 🚀 Voor Nieuwe Gebruikers: Snel Aan de Slag

**Je collega heeft dit pakket gedownload van GitHub, uitgepakt, en wil het nu gebruiken.**  
Dit is de eenvoudigste manier om te starten, zonder technische voorkennis.

### Wat Heb Je Nodig?

- **Python 3.12 of hoger** geïnstalleerd op je Windows computer
  - [Download Python hier](https://www.python.org/downloads/) als je het nog niet hebt
  - Tijdens installatie: vink "Add Python to PATH" aan!

### Stap 1: Download en Uitpakken (Eenmalig)

1. Download het project als ZIP van GitHub
2. Pak het uit naar een map op je computer (bijv. `C:\Users\JouwNaam\transform-myd-minimal`)
3. Open **PowerShell** in die map:
   - In de bestandsverkenner: klik rechts op de map → "Open in Terminal" of "Open PowerShell hier"

### Stap 2: Installatie (Eenmalig - 2 minuten)

**Waarom?** Python heeft extra modules (libraries) nodig om te werken. Deze stap installeert alles automatisch.

```powershell
# Voer dit commando uit in PowerShell:
py -3.12 dev_bootstrap.py
```

**Wat gebeurt er?**
- Er wordt een virtuele omgeving (`.venv`) aangemaakt
- Alle benodigde software wordt geïnstalleerd
- Je hoeft dit maar één keer te doen!

**Problemen?** Zie de [Veelgestelde Vragen](#veelgestelde-vragen--problemen-oplossen) onderaan.

### Stap 3: Het Programma Gebruiken

**Er zijn 3 hoofdcommando's die je na elkaar uitvoert:**

#### Commando 1: `index_source` - Brongegevens Inlezen
**Wat doet het?** Leest de kolomnamen uit je Excel-bestand met brondata.

```powershell
py -3.12 -m transform_myd_minimal index_source --object m140 --variant bnka
```

**Je moet hebben:** Een bestand `data/01_source/m140_bnka.xlsx` met je brondata.

**Het maakt aan:** `migrations/m140/bnka/index_source.yaml` met alle kolomnamen.

---

#### Commando 2: `index_target` - Doelvelden Inlezen
**Wat doet het?** Leest welke velden SAP verwacht (uit een XML-bestand).

```powershell
py -3.12 -m transform_myd_minimal index_target --object m140 --variant bnka
```

**Je moet hebben:** Een bestand `data/02_target/m140_bnka.xml` met SAP velddefinities.

**Het maakt aan:** `migrations/m140/bnka/index_target.yaml` met alle SAP-velden.

---

#### Commando 3: `map` - Koppeling Maken
**Wat doet het?** Koppelt automatisch je bronkolommen aan de SAP-velden.

```powershell
py -3.12 -m transform_myd_minimal map --object m140 --variant bnka
```

**Je moet hebben:** De output van stap 1 en 2 (de twee YAML-bestanden).

**Het maakt aan:** `migrations/m140/bnka/mapping.yaml` met de koppelingen.

---

### Belangrijk: Object en Variant

- `--object m140`: De naam van je dataset (bijv. banken = m140, profit centers = m120)
- `--variant bnka`: De specifieke tabel variant (bijv. BNKA voor bankgegevens)

**Vervang deze waardes** met jouw eigen object/variant namen!

### Snel Overzicht: Alle 3 Stappen

```powershell
# Stap 1: Brondata indexeren
py -3.12 -m transform_myd_minimal index_source --object m140 --variant bnka

# Stap 2: Doelvelden indexeren
py -3.12 -m transform_myd_minimal index_target --object m140 --variant bnka

# Stap 3: Mapping genereren
py -3.12 -m transform_myd_minimal map --object m140 --variant bnka
```

### Hulp Nodig?

- **Voor meer details:** Zie [SETUP.md](docs/SETUP.md) en [USAGE.md](docs/USAGE.md)
- **Problemen?** Zie [Veelgestelde Vragen](#veelgestelde-vragen--problemen-oplossen) hieronder
- **Alle commando's:** Voer uit: `py -3.12 -m transform_myd_minimal --help`

---

## 📚 Veelgestelde Vragen & Problemen Oplossen

### ❌ "Python is not recognized" of "py is not recognized"

**Probleem:** Windows kan Python niet vinden.

**Oplossing:**
1. Installeer Python van [python.org/downloads](https://www.python.org/downloads/)
2. **Belangrijk:** Vink "Add Python to PATH" aan tijdens installatie!
3. Herstart PowerShell na installatie
4. Test met: `py --version` (moet iets tonen zoals "Python 3.12.0")

---

### ❌ "File not found: data/01_source/m140_bnka.xlsx"

**Probleem:** Het programma kan je bronbestand niet vinden.

**Oplossing:**
1. Controleer of je bestand op de juiste locatie staat:
   - Voor `index_source`: `data/01_source/m140_bnka.xlsx`
   - Voor `index_target`: `data/02_target/m140_bnka.xml`
2. Controleer de bestandsnaam (inclusief object/variant)
3. Let op hoofdletters/kleine letters in de bestandsnaam!

---

### ❌ "cannot be loaded because running scripts is disabled"

**Probleem:** PowerShell mag geen scripts uitvoeren (Windows beveiliging).

**Oplossing:**
```powershell
# Voer dit uit in PowerShell (als Administrator):
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Dan werkt het programma normaal
py -3.12 -m transform_myd_minimal --help
```

---

### ❌ "No module named 'transform_myd_minimal'"

**Probleem:** De installatie is niet compleet.

**Oplossing:**
```powershell
# Voer de installatie opnieuw uit:
py -3.12 dev_bootstrap.py

# Als dat niet werkt, probeer handmatig:
py -3.12 -m pip install -e .
```

---

### ❌ "Output file exists. Use --force to overwrite"

**Probleem:** Er bestaat al output van een eerdere run.

**Oplossing:**
```powershell
# Voeg --force toe om te overschrijven:
py -3.12 -m transform_myd_minimal index_source --object m140 --variant bnka --force
```

---

### ❌ Ik wil de virtuele omgeving handmatig activeren

**Waarom?** Makkelijker typen als je veel commando's achter elkaar uitvoert.

**Oplossing:**
```powershell
# Activeer de virtuele omgeving:
.\.venv\Scripts\Activate.ps1

# Nu kun je korter typen (zonder "py -3.12 -m"):
python -m transform_myd_minimal --help
python -m transform_myd_minimal index_source --object m140 --variant bnka

# Om te deactiveren (terug naar normaal):
deactivate
```

---

### ❓ Waar vind ik mijn output bestanden?

**Antwoord:**
- **YAML-bestanden:** In `migrations/{object}/{variant}/`
  - `index_source.yaml` - Jouw bronkolommen
  - `index_target.yaml` - SAP doelvelden
  - `mapping.yaml` - Koppelingen tussen bron en doel
- **Log-bestanden:** In `data/99_logging/`
- **Rapporten (HTML):** In `data/03_index_source/`, `data/04_index_target/`, `data/05_map/`

---

### ❓ Hoe weet ik of het gelukt is?

**Antwoord:**  
Als het commando succesvol is, zie je:
- Groene tekst met "✓ Success" of vergelijkbare bevestiging
- Een bericht over waar de output is opgeslagen
- Geen rode error-meldingen

Je kunt de output-bestanden openen met een teksteditor (zoals Notepad++) om te controleren.

---

## 📖 Voor Meer Informatie

- **[SETUP.md](docs/SETUP.md)** - Gedetailleerde installatie-instructies en alternatieve methoden
- **[USAGE.md](docs/USAGE.md)** - Complete gebruiksvoorbeelden en workflows
- **[CLI_OPTIONS.md](docs/CLI_OPTIONS.md)** - Alle beschikbare commando's en opties
- **[DIRECTORY_STRUCTURE.md](docs/DIRECTORY_STRUCTURE.md)** - Uitleg over alle mappen en bestanden
- **[CONTRIBUTING.md](docs/CONTRIBUTING.md)** - Voor ontwikkelaars die code willen aanpassen

---

## 💻 Technische Quick Start (Voor Ervaren Gebruikers)

```powershell
# One-time setup (creates .venv and installs ALL deps)
py -3.12 dev_bootstrap.py

# Run the CLI - choose your preferred method:
.\scripts\transform-myd-minimal.ps1 --help                          # PowerShell wrapper (recommended)
py -3.12 -m transform_myd_minimal --help                             # Python module (always works)
.\.venv\Scripts\python.exe -m transform_myd_minimal --help           # After venv activation
```

**Recommended for Windows PowerShell:**
- Use the **wrapper scripts**: `.\transform-myd-minimal.ps1` (PowerShell) or `transform-myd-minimal.bat` (CMD)
- These automatically use the venv Python and all dependencies
- Or use: `py -3.12 -m transform_myd_minimal <command>`

Als je dev_bootstrap niet wilt gebruiken:

```powershell
# Handmatige installatie (runtime deps)
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
py -3.12 -m pip install -U pip setuptools wheel
py -3.12 -m pip install -r requirements.txt

# Optioneel: ontwikkel-setup (editable + dev extras)
py -3.12 -m pip install -e ".[dev]"
```

---

## Quality Assurance & Development Tools

This project uses a modern QA toolchain to ensure code quality:

### 🔍 Code Quality Tools

- **Ruff**: Fast Python linter for code quality checks
- **Black**: Automatic code formatter for consistent style
- **mypy**: Static type checker for type safety
- **pytest**: Testing framework with coverage reporting
- **pre-commit**: Git hooks for automated quality checks

### 🚀 Quick QA Commands

```bash
# Run linter
ruff check src/ tests/

# Auto-fix linting issues
ruff check --fix src/ tests/

# Format code
black src/ tests/

# Type checking
mypy src/

# Run tests
pytest tests/ -v

# Run tests with coverage
pytest tests/ --cov=src/transform_myd_minimal --cov-report=term

# Install pre-commit hooks
pre-commit install

# Run all pre-commit checks
pre-commit run --all-files
```

See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for detailed development guidelines.

## 🔒 Schema Validation

Transform MYD Minimal includes built-in schema validation for all configuration and output files using Pydantic. This ensures data integrity and provides clear error messages when files don't match expected formats.

### Validated Files

- **config.yaml**: Main configuration file with fuzzy matching, directory settings, and mapping configuration
- **central_mapping_memory.yaml**: Central mapping memory with skip rules, manual mappings, and synonyms
- **index_source.yaml**: Source field index generated by `index_source` command
- **index_target.yaml**: Target field index generated by `index_target` command
- **mapping.yaml**: Field mapping results generated by `map` command

### How Validation Works

Validation happens automatically when files are loaded:
- **At startup**: Config files are validated when loaded
- **During commands**: Output files are validated when read by subsequent commands
- **Clear errors**: If validation fails, you'll get informative error messages indicating exactly what's wrong

### Example Error Messages

```bash
# Invalid fuzzy_threshold in config.yaml
ValidationError: Config validation failed: fuzzy_threshold must be between 0.0 and 1.0

# Missing required field in central_mapping_memory.yaml
ValidationError: Central mapping memory validation failed: Field required [source_description]

# Empty source_fields in index_source.yaml
ValidationError: Index source validation failed: source_fields cannot be empty
```

### Extending Schemas

If you need to extend or modify schemas:

1. Edit the schema models in `src/transform_myd_minimal/schema.py`
2. Update the corresponding validation function if needed
3. Add tests to `tests/test_schema_validation.py` to verify your changes
4. Run tests: `pytest tests/test_schema_validation.py -v`

### No Breaking Changes

Schema validation is designed to be backward compatible:
- All valid existing files continue to work
- Only invalid files (that would have caused runtime errors) are rejected
- Error messages guide you to fix issues quickly

## Verdere Documentatie
- [Gebruik - USAGE.md](docs/USAGE.md)
- [Directory Structure - DIRECTORY_STRUCTURE.md](docs/DIRECTORY_STRUCTURE.md)
- [Logging - LOGGING.md](docs/LOGGING.md)
- [Development Setup - DEVELOPMENT.md](docs/DEVELOPMENT.md)
- [CLI Opties - CLI_OPTIONS.md](docs/CLI_OPTIONS.md)
- [Contributie - CONTRIBUTING.md](docs/CONTRIBUTING.md)
- [Changelog - CHANGELOG.md](docs/CHANGELOG.md)

## 🆕 NEW: Step-by-Step Workflow (v4.0)

Deze nieuwe workflow zorgt ervoor dat elke stap een aparte CLI-command is en alle output variant-specifiek wordt opgeslagen.

### Workflow Stappen

#### 1. index_source - Indexeer bronvelden

**Command:**  
```bash
# Linux/macOS
./transform-myd-minimal index_source --object {object} --variant {variant}

# Windows PowerShell
python -m transform_myd_minimal index_source --object {object} --variant {variant}
```

**Werking:**  
- Zoekt naar het bestand: `data/01_source/{object}_{variant}.xlsx`
- Parseert de headers uit deze XLSX
- Zet de velden om naar een YAML-structuur (`index_source.yaml`)
- Maakt (indien nodig) de folder: `migrations/{object}/{variant}/`
- Schrijft het resultaat naar: `migrations/{object}/{variant}/index_source.yaml`
- Voegt het object/variant toe aan de globale lijst: `migrations/object_list.yaml`
- Automatic log files: `data/99_logging/index_source_{object}_{variant}_{YYYYMMDD_HHmm}.jsonl`

#### 2. index_target - Indexeer doelvelden

**Command:**  
```bash
# Linux/macOS
./transform-myd-minimal index_target --object {object} --variant {variant}

# Windows PowerShell  
python -m transform_myd_minimal index_target --object {object} --variant {variant}
```

**Werking:**  
- Zoekt naar het bestand: `data/02_target/{object}_{variant}.xml`
- **Automatische fallback**: Als XML niet bestaat of niet leesbaar is, zoekt naar `{object}_{variant}.xlsx` 
- Parseert XML en filtert target fields behorend bij deze variant
- Bijvoorbeeld: Zoek velden die beginnen met `S_{variant}` zoals `S_BNKA` als variant=`bnka`
- Zet de target fields om naar YAML (`index_target.yaml`)
- Schrijft het resultaat naar: `migrations/{object}/{variant}/index_target.yaml`

**Xlsx Fallback (F02):**
- Automatische fallback naar `.xlsx` als `.xml` niet beschikbaar/leesbaar is
- Duidelijke melding welk bestand gebruikt wordt: "Fallback: file.xml niet gevonden, file.xlsx gebruikt"
- Optioneel: `--prefer-xlsx` om xlsx te prefereren boven xml

#### 3. map - Genereer mapping

**Command:**  
```bash
# Linux/macOS
./transform-myd-minimal map --object {object} --variant {variant}

# Windows PowerShell
python -m transform_myd_minimal map --object {object} --variant {variant}
```

**Werking:**  
- Zoekt in `migrations/{object}/{variant}/` naar `index_source.yaml` en `index_target.yaml`
- Maakt een match tussen source en target fields (met confidence score en audit/logging)
- Schrijft het resultaat naar: `migrations/{object}/{variant}/mapping.yaml`

### 📁 Nieuwe Directorystructuur

```
data/
  01_source/                     # Source Excel files (F01)
    m140_bnka.xlsx              # Source headers 
  02_target/                     # Target XML files (F02)
    m140_bnka.xml               # Target field definitions
  03_index_source/               # F01 HTML/JSON reports
    index_source_20240923_0423.{html,json}
  04_index_target/               # F02 HTML/JSON reports  
    index_target_20240923_0428.{html,json}
  05_map/                        # F03 HTML/JSON reports
    mapping_20240923_0430.{html,json}
  06_template/                   # CSV templates (F04)
    S_BNKA#*.csv                # Template files for variant
  07_raw/                        # Raw data for transformation (F04)
    m140_bnka.xlsx              # Raw data input
  08_raw_validation/             # Raw validation outputs
  09_rejected/                   # Rejected records
  10_transformed/                # Final CSV outputs (F04)
  11_transformed_validation/     # Post-transform validation
  99_logging/                    # Log files (all steps)

migrations/
  m140/                          # Per object
    bnka/                        # Per variant 
      index_source.yaml          # F01 output
      index_target.yaml          # F02 output  
      mapping.yaml               # F03 output
```
migrations/
  object_list.yaml               # Global object/variant registry
  m140/
    bnka/
      index_source.yaml          # Indexed source fields
      index_target.yaml          # Indexed target fields  
      mapping.yaml               # Generated mappings
```

### 🚀 Quick Start Example

```bash
# 1. Indexeer source velden
./transform-myd-minimal index_source --object m140 --variant bnka

# 2. Indexeer target velden
./transform-myd-minimal index_target --object m140 --variant bnka

# 3. Genereer mapping
./transform-myd-minimal map --object m140 --variant bnka
```

### 📋 Enhanced Logging

**Logging is on by default** for `index_source` and `index_target` commands with rich formatting and automatic file logging.

**Default behavior:**
- Interactive terminal → Human summary + preview table
- Piped/redirected → JSONL lines
- Automatic log files: `data/99_logging/<step>_<object>_<variant>_<YYYYMMDD_HHmm>.jsonl`

**Examples:**
```bash
# Default (human format in terminal, JSONL when piped)
./transform-myd-minimal index_source --object m140 --variant bnka

# Force JSONL output
./transform-myd-minimal index_source --object m140 --variant bnka --json

# Quiet mode (no stdout, but still writes log file)
./transform-myd-minimal index_source --object m140 --variant bnka --quiet

# No log file
./transform-myd-minimal index_source --object m140 --variant bnka --no-log-file
```

See [LOGGING.md](docs/LOGGING.md) for complete documentation.

### 📊 Rapportage per stap (F01–F04)

Elke workflow stap genereert automatisch zowel JSON als **self-contained HTML rapporten** met interactieve visualisaties:

#### 🎯 HTML Rapportage Features
- **Self-contained**: Alle CSS/JS inline embedded, geen externe dependencies
- **Interactief**: Client-side sorting, filtering en zoeken in tabellen
- **Visueel**: KPI cards, bar charts (inline SVG), responsive design
- **Export**: CSV-downloadknoppen voor alle data (client-side generatie)
- **Embedded data**: JSON data in `<script id="data">` tag voor verdere analyse

#### 📁 Rapportage Locaties

**F01-F03 (rapportage):**
```
data/03_index_source/         # F01 HTML/JSON reports
├── index_source_YYYYMMDD_HHMM.{html,json}

data/04_index_target/         # F02 HTML/JSON reports  
├── index_target_YYYYMMDD_HHMM.{html,json}

data/05_map/                  # F03 HTML/JSON reports
└── mapping_YYYYMMDD_HHMM.{html,json}
```

**F04 (validatie):**
```
data/08_raw_validation/      # RAW validatie
├── raw_validation_<object>_<variant>_<ts>.{html,json,jsonl}

data/11_transformed_validation/  # POST-transform validatie  
├── post_transform_validation_<object>_<variant>_<ts>.{html,json,jsonl}
```

#### 🎛️ CLI Opties
```bash
# HTML rapportage uitschakelen
./transform-myd-minimal index_source --object m140 --variant bnka --no-html

# Custom rapportage directory
./transform-myd-minimal map --object m140 --variant bnka --html-dir /custom/reports

# HTML staat standaard AAN; JSON/JSONL blijven ongewijzigd
```

#### 📋 Rapportage Inhoud per Stap

**F01 (index_source)**: Headers analyse
- KPI: total columns, duplicates, empty headers  
- Headers tabel: field name, dtype, nullable, example
- Duplicates lijst en warnings

**F02 (index_target)**: Target fields analyse
- KPI: total fields, mandatory, keys
- Field groups distributie chart (key vs control data)
- Target fields tabel: SAP field, table, mandatory, key, data type, length
- Validation scaffold status

**F03 (map)**: Mapping resultaten
- KPI: mapped, unmapped, to-audit, unused sources
- Mappings tabel: target field, source header, confidence, status, rationale
- To-audit items voor handmatige review
- Unmapped source/target fields lijsten

**F04 (transform)**: Validatie rapporten
- **RAW**: rows in, null rates by source, missing sources
- **POST**: rows in/out/rejected, coverage %, errors by rule/field, sample rejected rows
- CSV export requirements (UTF-8, CRLF, etc.) voor POST rapport

### ✅ Voordelen Nieuwe Workflow

- **Stapsgewijze controle**: Elke stap kan afzonderlijk uitgevoerd worden
- **Variant-specifieke output**: Geen globale bestanden meer
- **Heldere input/output paden**: Duidelijk waar data vandaan komt en naartoe gaat
- **Auditeerbaar**: Elke stap logt wat gedaan wordt
- **Uitbreidbaar**: Nieuwe stappen kunnen eenvoudig toegevoegd worden

---

## Legacy Multi-File YAML Migration Workflow (v3.x)

## 🆕 Source-Based Mapping Generation (v3.1)

Implementeert directe mappinggeneratie vanuit de bronbestanden i.p.v. fields.xlsx:

### ✅ Ondersteunde Bronbestanden
- **Source headers (XLSX)**: `data/01_source/BNKA_headers.xlsx` - bevat source system veldnamen als kolomkoppen
- **Target velden (SpreadsheetML)**: `data/01_source/Source data for Bank.xml` - Excel 2003 XML met target field metadata

### 🎯 Source-Based Workflow
```bash
# Direct mapping genereren uit bronbestanden (standaard met from_sources: true)
./transform-myd-minimal map -object test -variant test

# Met CLI overrides
./transform-myd-minimal map -object test -variant test \
  --source-headers-xlsx "data/01_source/BNKA_headers.xlsx" \
  --target-xml "data/01_source/Source data for Bank.xml" \
  --target-xml-worksheet "Field List"
```

### 📊 Output Artifacts
- **config/targets.yaml**: Target field metadata met internal_id en transformer_id
- **config/mapping.yaml**: Source-to-target mappings met confidence scores en match methods

### ⚙️ Configuratie Priority
CLI arguments > config.yaml instellingen voor maximum flexibiliteit:
- `--source-headers-xlsx`: Overschrijft config.yaml pad
- `--source-headers-sheet`: Overschrijft sheet naam
- `--source-headers-row`: Overschrijft header rij nummer
- `--target-xml`: Overschrijft XML bestand pad
- `--target-xml-worksheet`: Overschrijft worksheet naam

### 🔧 Config.yaml Uitbreiding
```yaml
mapping:
  from_sources: true

  source_headers:
    path: data/01_source/BNKA_headers.xlsx
    sheet: Sheet1
    header_row: 1
    ignore_data_below: true

  target_xml:
    path: data/01_source/Source data for Bank.xml
    worksheet_name: "Field List"
    header_match:
      sheet_name: "Sheet Name"
      group_name: "Group Name"
      description: "Field Description"
      # ... etc
    normalization:
      strip_table_prefix: "S_"
      uppercase_table_field: true
    output_naming:
      transformer_id_template: "{sap_table}#{sap_field}"
      internal_id_template: "{internal_table}.{sap_field}"

matching:
  target_label_priority:
    - description
    - sap_field
    - group_name
```

## 🆕 New Multi-File Migration Structure (v3.0)

De nieuwe multi-file YAML structuur lost de pijnpunten van de vorige single-file aanpak op:

### ✅ Voordelen van de Nieuwe Structuur
- **Clear separation of concerns**: Gescheiden veld definities, mappings, validatie regels en value transformaties
- **Non-redundant**: Informatie verschijnt slechts op één plek; geen duplicatie tussen bestanden
- **SAP object-anchored**: Migratie structuur volgt SAP business objecten
- **Table-scoped rules**: Value rules zijn tabel-specifiek, niet object-breed toegepast
- **Auditable decisions**: Volledige traceerbaarheid van mapping beslissingen met acceptance/rejection tracking

### 📁 Directory Structuur
```
migrations/
├── objects.yaml                           # Catalog van alle migratie objecten
├── M120/                                  # Profit Centers
│   └── cepc/                             # CEPC tabel variant
│       ├── fields.yaml                   # Target veld definities
│       ├── mappings.yaml                 # Source-naar-target mappings
│       ├── validation.yaml               # Validatie regels en constraints
│       └── transformations.yaml          # Value transformatie logica
├── M140/                                  # Banks
│   └── bnka/                             # BNKA tabel variant
│       ├── fields.yaml                   # Target veld definities
│       ├── mappings.yaml                 # Source-naar-target mappings
│       ├── validation.yaml               # Validatie regels en constraints
│       └── transformations.yaml          # Value transformatie logica
└── SCHEMA.md                             # Schema documentatie
```

### 🎯 Implementatie Status
- [x] **M120 (Profit Centers)**: Volledig geïmplementeerd met CEPC tabel voorbeeld
- [x] **M140 (Banks)**: Volledig geïmplementeerd met BNKA tabel voorbeeld  
- [x] **Schema documentatie**: Uitgebreide documentatie van file structuren
- [x] **Loader code**: Bijgewerkt om nieuwe structuur te genereren
- [x] **Backward compatibility**: Legacy config/ structuur blijft werken

## Features

### 🔄 Integrated YAML Workflow (v3.0)
- **Single command** genereert migration YAML bestanden 
- **Automatische generatie** van fields.yaml, mappings.yaml, validation.yaml, transformations.yaml
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
- **Centraal geheugenbestand** (`config/central_mapping_memory.yaml`) voor herbruikbare mapping regels
- **Skip rules** - velden uitsluiten van mapping met auditeerbare comments
- **Manual mappings** - handmatige veld-naar-veld mappings met business context
- **Global + table-specific overrides** - flexibele regel hiërarchie
- **Comments** worden bewaard in output voor transparante overdracht tussen collega's
- **Prioriteit**: Central memory regels worden eerst toegepast, daarna automatische matching

## 📦 Project Structuur

De repository gebruikt een moderne src-layout voor betere code organisatie:

```
transform-myd-minimal/
├── src/
│   └── transform_myd_minimal/          # Python package
│       ├── __init__.py                 # Package initialisatie
│       ├── __main__.py                 # Module entry point
│       ├── main.py                     # Hoofd orchestratie logica
│       ├── cli.py                      # CLI argument parsing
│       ├── config_loader.py            # Configuratie laden
│       ├── fuzzy.py                    # Fuzzy matching algoritmen
│       ├── generator.py                # YAML generatie logica
│       └── synonym.py                  # Synonym matching
├── transform-myd-minimal               # Wrapper script
├── config/                              # Centrale configuratie bestanden
│   ├── config.yaml                     # Applicatie configuratie
│   └── central_mapping_memory.yaml     # Centrale mapping regels
├── config/                             # Globale output bestanden (voor source-based mapping)
├── data/                               # Input data (Excel bestanden)
├── migrations/                         # Nieuwe multi-file structuur
└── README.md
```

**Voordelen van de src-layout:**
- Schone root directory zonder Python bestanden
- Package gebaseerde import structuur
- Betere separatie van code en configuratie
- Professionele Python project structuur

**⚠️ Belangrijke wijziging in CLI invocatie:**
Het script wordt nu aangeroepen via `./transform-myd-minimal` (wrapper script) in plaats van direct via Python bestanden. Dit zorgt voor een schonere interface zonder zichtbare `.py` extensies.

- **Oud**: `python3 transform_myd_minimal.py map -object m140 -variant bnka`
- **Nieuw**: `./transform-myd-minimal map -object m140 -variant bnka`

De wrapper script zorgt automatisch voor de juiste Python module aanroep en path configuratie.

## Gebruik

### ✨ Migration Structure Generation

Het systeem genereert nu alleen de nieuwe migration structuur:
- **Migration Files**: `migrations/{OBJECT}/{table}/` - Nieuwe multi-file structuur

```bash
# Genereert alleen nieuwe migration structuur
./transform-myd-minimal map -object m140 -variant bnka
```

**Output:**
```
=== Advanced Matching Results ===
... (matching details) ...

=== Generating New Multi-File Migration Structure ===
Generated: migrations/M140/bnka/fields.yaml
Generated: migrations/M140/bnka/mappings.yaml
Generated: migrations/M140/bnka/validation.yaml
Generated: migrations/M140/bnka/transformations.yaml
Generated 5 migration files in migrations/ directory
```

### 📋 Nieuwe Structure Voordelen

1. **Clear Separation**: Elke file heeft een specifieke verantwoordelijkheid
2. **SAP-Anchored**: Structuur volgt SAP business objecten (M120=CEPC, M140=BNKA)
3. **Table-Scoped**: Value rules zijn tabel-specifiek, niet object-breed
4. **Non-Redundant**: Geen dubbele informatie tussen bestanden
5. **Auditable**: Volledige traceerbaarheid van mapping beslissingen

### 🎯 Voorbeelden

#### M120 Profit Centers
```bash
./transform-myd-minimal map -object m120 -variant cepc
```
Genereert: `migrations/M120/cepc/` met alle 4 YAML bestanden

#### M140 Banks  
```bash
./transform-myd-minimal map -object m140 -variant bnka
```
Genereert: `migrations/M140/bnka/` met alle 4 YAML bestanden

### Nieuwe format (aanbevolen)
```bash
./transform-myd-minimal map -object <object_name> -variant <variant_name> [OPTIONS]
```

### Legacy format (backward compatible)
```bash
./transform-myd-minimal -object <object_name> -variant <variant_name> [OPTIONS]
```

### Basis Voorbeeld

```bash
# Nieuwe format
./transform-myd-minimal map -object m140 -variant bnka

# Legacy format (toont waarschuwing)
./transform-myd-minimal -object m140 -variant bnka
```

### Geavanceerde Opties

```bash
# Met aangepaste fuzzy threshold
./transform-myd-minimal map -object m140 -variant bnka --fuzzy-threshold 0.8

# Fuzzy matching uitschakelen
./transform-myd-minimal map -object m140 -variant bnka --disable-fuzzy

# Maximum suggesties aanpassen
./transform-myd-minimal map -object m140 -variant bnka --max-suggestions 5
```

## Command Line Opties

| Option | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| `map` | subcommand | Nee* | - | Genereer column mapping en YAML files |
| `-object OBJECT` | string | **Ja** | - | Object naam (bijv. m140) |
| `-variant VARIANT` | string | **Ja** | - | Variant naam (bijv. bnka) |
| `--fuzzy-threshold` | float | Nee | 0.6** | Fuzzy matching threshold (0.0-1.0) |
| `--max-suggestions` | int | Nee | 3** | Maximum fuzzy match suggesties |
| `--disable-fuzzy` | flag | Nee | False** | Fuzzy matching uitschakelen |

*Het `map` subcommand is optioneel voor backward compatibility  
**Default waarden kunnen worden aangepast via config.yaml

Voor een volledig overzicht van alle CLI opties, zie: **[CLI_OPTIONS.md](docs/CLI_OPTIONS.md)**

## Configuratie (config/config.yaml)

Het script ondersteunt een centraal configuratiebestand `config/config.yaml` voor het instellen van default waarden. CLI argumenten hebben altijd voorrang op config.yaml instellingen.

### Ondersteunde Parameters

```yaml
# Transform MYD Minimal Configuration
# Default object and variant (optional - can be overridden by CLI)
object: "m140"       # Default object name
variant: "bnka"      # Default variant name

# Fuzzy matching configuration
fuzzy_threshold: 0.6        # Fuzzy matching threshold (0.0-1.0)
max_suggestions: 3          # Maximum number of fuzzy match suggestions  
disable_fuzzy: false        # Whether to disable fuzzy matching

# Directory configuration
input_dir: "data/01_source" # Input directory for Excel files
output_dir: "output"        # Output directory for generated YAML files
```

### Parameter Beschrijvingen

| Parameter | Type | Default | Beschrijving |
|-----------|------|---------|--------------|
| `object` | string | - | Default object naam (bijv. m140) |
| `variant` | string | - | Default variant naam (bijv. bnka) |
| `fuzzy_threshold` | float | 0.6 | Fuzzy matching threshold (0.0-1.0) |
| `max_suggestions` | int | 3 | Maximum aantal fuzzy match suggesties |
| `disable_fuzzy` | boolean | false | Schakel fuzzy matching uit |
| `input_dir` | string | "data/01_source" | Input directory voor Excel bestanden |
| `output_dir` | string | "output" | Output directory voor YAML bestanden |

### Voorrang (Precedence)

1. **CLI argumenten** - Hoogste prioriteit
2. **config/config.yaml** - Middel prioriteit  
3. **Hardcoded defaults** - Laagste prioriteit

**Opmerking**: Het systeem zoekt naar configuratiebestanden in de `config/` directory.

### Voorbeelden

```bash
# Basic command (object and variant required)
./transform-myd-minimal map --object m140 --variant bnka

# With config defaults (object/variant can be set in config/config.yaml)
./transform-myd-minimal map

# Override config defaults with CLI arguments
./transform-myd-minimal map --object m150 --variant cepc --fuzzy-threshold 0.8

# Configuratie wordt automatisch geladen als config/config.yaml bestaat
# Anders worden hardcoded defaults gebruikt
```

### Snelle Referentie

**Minimaal commando:**
```bash
# Met expliciete argumenten
./transform-myd-minimal map --object m140 --variant bnka

# Met config defaults (object/variant in config.yaml)
./transform-myd-minimal map
```

**Voorbeeld config.yaml met alle CLI opties:**
```yaml
# Standaard object en variant (optioneel) 
object: "m140"
variant: "bnka"

# Fuzzy matching instellingen
fuzzy_threshold: 0.7
max_suggestions: 5
disable_fuzzy: false

# Directory instellingen  
input_dir: "data/01_source"
output_dir: "output"
```

**Belangrijke CLI opties:**
- `--fuzzy-threshold FLOAT`: Fuzzy matching threshold (0.0-1.0, default: config.yaml of 0.6)
- `--max-suggestions INT`: Maximum aantal fuzzy match suggesties (default: config.yaml of 3)
- `--disable-fuzzy`: Schakel fuzzy matching uit
- `config/config.yaml`: Centraal configuratiebestand voor default waarden

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
1. Leest het bestand `data/01_source/fields_{object}_{variant}.xlsx`
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
- `data/01_source/fields_{object}_{variant}.xlsx` - Input Excel bestand
- `config/{object}/{variant}/column_map.yaml` - Output YAML bestand (wordt gegenereerd)

## Help

```bash
./transform-myd-minimal --help
```

**Uitgebreide CLI documentatie**: Zie [CLI_OPTIONS.md](docs/CLI_OPTIONS.md) voor alle opties, voorbeelden en changelog.

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

Het central mapping memory systeem maakt gebruik van een centraal configuratiebestand (`config/central_mapping_memory.yaml`) voor herbruikbare mapping regels.

**Opmerking**: Het systeem zoekt naar configuratiebestanden in de `config/` directory.

### 📋 Configuratie Structuur

Het `config/central_mapping_memory.yaml` bestand ondersteunt:

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

## Geïntegreerde Migration Generator

De migration generator is geïntegreerd in het hoofdscript. Bij elke `map` opdracht worden automatisch alle benodigde migration YAML-bestanden gegenereerd:

**Automatisch gegenereerde bestanden:**
1. **objects.yaml** - Catalog van alle migratie objecten 
2. **fields.yaml** per table - Target veld definities uit Excel-bestanden  
3. **mappings.yaml** per table - Source-naar-target mappings met confidence scores
4. **validation.yaml** per table - Validatie regels en constraints
5. **transformations.yaml** per table - Value transformatie logica

**Gebruik:**
```bash
# Genereert alle migration files automatisch
./transform-myd-minimal map -object m140 -variant bnka
```

**Gegenereerde bestanden:**
- `migrations/objects.yaml` - Master catalog (updated bij elke run)
- `migrations/{OBJECT}/{table}/fields.yaml` - Per table velddefinities
- `migrations/{OBJECT}/{table}/mappings.yaml` - Per table mappings
- `migrations/{OBJECT}/{table}/validation.yaml` - Per table validatie regels
- `migrations/{OBJECT}/{table}/transformations.yaml` - Per table transformaties

Het script scant automatisch de bestaande Excel-bestanden in `data/01_source/fields_{object}_{variant}.xlsx`.

## Versie Informatie

**Huidige versie: 4.1.0 - Step-by-Step Object+Variant Pipeline with HTML Reporting**

```bash
# Bekijk versie informatie
./transform-myd-minimal --version
```

### Versie Geschiedenis
- **v4.1** - HTML reporting voor alle F01-F04 stappen
- **v4.0** - Step-by-Step Object+Variant Pipeline met F01-F04 commands
- **v3.0** - Geïntegreerde YAML workflow met `map` subcommand
- **v2.0** - Advanced matching algoritmen (fuzzy, synonym)
- **v1.0** - Basis exact matching functionaliteit

Voor volledige documentatie zie [CLI_OPTIONS.md](docs/CLI_OPTIONS.md)
