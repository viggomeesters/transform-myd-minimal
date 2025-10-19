# Setup Guide - Transform MYD Minimal

Volg deze stappen om het project op je computer te laten werken.

## ✅ Vereisten

Zorg dat je deze hebt geïnstalleerd:
- **Python 3.11 of hoger** - [Download van python.org](https://www.python.org/downloads/) (aanbevolen: 3.12)
- **Git** (optioneel, voor cloning) - [Download van git-scm.com](https://git-scm.com/download/win)

### Check of Python is geïnstalleerd:
```powershell
python --version
py --version
```

## 🚀 Installatie (5 minuten)

### Optie 1: Snelle setup (aanbevolen)

```powershell
# 1. Clone het project (of download en unzip)
git clone https://github.com/viggomeesters/transform-myd-minimal.git
cd transform-myd-minimal

# 2. Eenmalige setup (maakt venv en installeert alles)
py -3.12 dev_bootstrap.py

# 3. Klaar! Test het:
.\transform-myd-minimal.ps1 --help
```

### Optie 2: Handmatige setup

```powershell
# 1. Ga naar de project folder
cd transform-myd-minimal

# 2. Maak virtual environment
py -3.12 -m venv .venv

# 3. Activeer het
.\.venv\Scripts\Activate.ps1

# 4. Installeer dependencies
py -3.12 -m pip install -U pip setuptools wheel
py -3.12 -m pip install -r requirements.txt

# 5. Installeer het project (editable)
py -3.12 -m pip install -e .

# 6. Test het:
.\transform-myd-minimal.ps1 --help
```

## 💻 Hoe gebruik je het

### Methode 1: PowerShell wrapper (aanbevolen)
```powershell
.\scripts\transform-myd-minimal.ps1 --help
.\scripts\transform-myd-minimal.ps1 transform --object f100 --variant aufk --force
.\scripts\transform-myd-minimal.ps1 index_source --object m140 --variant bnka
```

### Methode 2: Python module (altijd betrouwbaar)
```powershell
py -3.12 -m transform_myd_minimal --help
py -3.12 -m transform_myd_minimal transform --object f100 --variant aufk --force
```

### Methode 3: Met venv geactiveerd
```powershell
# Eenmalig activeren
.\.venv\Scripts\Activate.ps1

# Dan kun je dit gebruiken:
.\.venv\Scripts\python.exe -m transform_myd_minimal --help
.\.venv\Scripts\python.exe -m transform_myd_minimal transform --object f100 --variant aufk --force
```

## 📋 Beschikbare Commando's

```powershell
# Help tonen
.\scripts\transform-myd-minimal.ps1 --help

# Source velden indexeren uit XLSX
.\scripts\transform-myd-minimal.ps1 index_source --object m140 --variant bnka

# Target velden indexeren uit XML
.\scripts\transform-myd-minimal.ps1 index_target --object m140 --variant bnka

# Mapping genereren
.\scripts\transform-myd-minimal.ps1 map --object m140 --variant bnka

# Transformatie uitvoeren
.\scripts\transform-myd-minimal.ps1 transform --object f100 --variant aufk --force
```

## 🐛 Problemen?

### Probleem: "Python not found"
```powershell
# Oplossing: Python toevoegen aan PATH of dit gebruiken:
py -3.12 dev_bootstrap.py
```

### Probleem: "No module named transform_myd_minimal"
```powershell
# Zorg dat je de venv hebt geactiveerd:
.\.venv\Scripts\Activate.ps1

# Of voer dev_bootstrap opnieuw uit:
py -3.12 dev_bootstrap.py
```

### Probleem: "Permission denied" bij .ps1 scripts
```powershell
# PowerShell execution policy instellen:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Dan kun je het script runnen:
.\transform-myd-minimal.ps1 --help
```

### Probleem: "lxml module not found"
```powershell
# Dit zou niet moeten gebeuren, maar als het gebeurt:
.\.venv\Scripts\python.exe -m pip install lxml

# Of voer dev_bootstrap opnieuw uit:
py -3.12 dev_bootstrap.py
```

## 📖 Documentatie

- [Gebruik - USAGE.md](USAGE.md)
- [Directory Structure - DIRECTORY_STRUCTURE.md](DIRECTORY_STRUCTURE.md)
- [Development Setup - DEVELOPMENT.md](DEVELOPMENT.md)
- [Logging - LOGGING.md](LOGGING.md)
- [CLI Opties - CLI_OPTIONS.md](CLI_OPTIONS.md)
- [Contributie - CONTRIBUTING.md](CONTRIBUTING.md)

## ✨ Tips

1. **Voer dev_bootstrap uit** als je ooit problemen hebt - het herstelt alles
2. **Gebruik de .ps1 wrapper** - deze zorgt dat alles goed werkt
3. **Activeer het venv** voor comfortabeler werken in dezelfde terminal sessie
4. **Zorg dat je output folders** (`data/`, `migrations/`) hebben schrijfrechten

## 🆘 Nog vragen?

Check de [README.md](README.md) of open een issue op GitHub.

---

**Happy transforming! 🚀**
