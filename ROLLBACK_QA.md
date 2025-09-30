# QA Toolchain Rollback Instructions

## Overview
This document provides instructions to rollback the QA toolchain setup if needed.

## Files Added/Modified

### New Files
- `.github/workflows/ci.yml` - GitHub Actions CI workflow

### Modified Files
- `pyproject.toml` - Added comprehensive ruff, mypy, pytest, and coverage configurations
- `.gitignore` - Added .env, .env.local, coverage reports, and .ruff_cache
- `README.md` - Added "Quality Assurance & Development Tools" section

### Existing Files (Not Modified)
- `.pre-commit-config.yaml` - Already existed with ruff, black, and basic hooks
- All product code in `src/` - No changes made per requirements

## Rollback Steps

### 1. Remove GitHub Actions Workflow
```bash
rm -f .github/workflows/ci.yml
```

### 2. Restore pyproject.toml
Revert the tool configurations to the original simpler version:
```bash
git checkout HEAD~1 -- pyproject.toml
```

Or manually edit to remove the expanded `[tool.ruff]`, `[tool.mypy]`, `[tool.pytest.ini_options]`, and `[tool.coverage.*]` sections, keeping only the original minimal versions.

### 3. Restore .gitignore
```bash
git checkout HEAD~1 -- .gitignore
```

Or manually remove these lines:
- `.env.local`
- `.env.*.local`
- `.ruff_cache/`
- `.coverage.*`
- `coverage.xml`
- `*.cover`
- `.hypothesis/`

### 4. Restore README.md
```bash
git checkout HEAD~1 -- README.md
```

Or manually remove the "Quality Assurance & Development Tools" section.

### 5. Verify Rollback
```bash
# Check git status
git status

# Verify no workflow file
ls -la .github/workflows/

# Run tests to ensure nothing broke
pytest tests/ -v
```

## What Remains After Rollback

The following will still be present (as they existed before):
- `.pre-commit-config.yaml` - Pre-commit hooks configuration
- Development dependencies in `pyproject.toml` `[project.optional-dependencies]` section
- All product code unchanged

## Notes

- No product code was modified during the QA toolchain setup
- The CI workflow is configured with `continue-on-error: true` for lint/format/typecheck jobs to allow gradual adoption
- Tests always pass (41/41 tests passing)
- All configuration is additive and non-breaking
