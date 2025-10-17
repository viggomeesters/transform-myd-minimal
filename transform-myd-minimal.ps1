#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Wrapper script for transform-myd-minimal CLI
    
.DESCRIPTION
    Ensures the virtual environment Python is used to run transform-myd-minimal commands.
    
.EXAMPLE
    .\transform-myd-minimal.ps1 transform --object f100 --variant aufk --force
    .\transform-myd-minimal.ps1 index_source --object m140 --variant bnka
    .\transform-myd-minimal.ps1 --help
#>

# Get the directory where this script is located
$ScriptDir = Split-Path -Parent -Path $MyInvocation.MyCommand.Definition

# Use the venv Python executable
$VenvPython = Join-Path $ScriptDir ".venv" "Scripts" "python.exe"

# Check if venv exists
if (-Not (Test-Path $VenvPython)) {
    Write-Error "Virtual environment not found at: $VenvPython"
    Write-Error "Please run: py -3.12 dev_bootstrap.py"
    exit 1
}

# Run the command with venv Python in module mode
& $VenvPython -m transform_myd_minimal @args
