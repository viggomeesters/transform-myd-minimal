@echo off
REM Wrapper script for transform-myd-minimal CLI (Windows CMD)
REM 
REM Usage: transform-myd-minimal transform --object f100 --variant aufk --force
REM        transform-myd-minimal index_source --object m140 --variant bnka
REM        transform-myd-minimal --help

setlocal enabledelayedexpansion

REM Get the directory where this script is located
set "SCRIPT_DIR=%~dp0"
set "VENV_PYTHON=%SCRIPT_DIR%.venv\Scripts\python.exe"

REM Check if venv exists
if not exist "%VENV_PYTHON%" (
    echo Error: Virtual environment not found at: %VENV_PYTHON%
    echo Please run: py -3.12 dev_bootstrap.py
    exit /b 1
)

REM Run the command with venv Python in module mode
"%VENV_PYTHON%" -m transform_myd_minimal %*
exit /b %errorlevel%
