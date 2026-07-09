#!/usr/bin/env pwsh
<#
.SYNOPSIS
    ZAI Coder CLI — Windows Build Script (PowerShell)

.DESCRIPTION
    Builds a standalone Windows executable for ZAI Coder CLI using PyInstaller.
    Creates dist/zai-coder.exe with all dependencies bundled.

.PARAMETER SkipVenv
    Skip creating a virtual environment (use current Python).

.PARAMETER Installer
    Also build an NSIS installer (requires NSIS installed).

.PARAMETER Clean
    Clean build artifacts before building.

.EXAMPLE
    .\build-windows.ps1
    .\build-windows.ps1 -Installer
    .\build-windows.ps1 -Clean -Installer
#>

param(
    [switch]$SkipVenv,
    [switch]$Installer,
    [switch]$Clean
)

$ErrorActionPreference = "Stop"
$Version = "1.23.0"
$ProjectRoot = $PSScriptRoot

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  ZAI Coder CLI v$Version — Windows Build" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# ── Clean ────────────────────────────────────────────────────────────────
if ($Clean) {
    Write-Host "[1/6] Cleaning build artifacts..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force "$ProjectRoot\build" -ErrorAction SilentlyContinue
    Remove-Item -Recurse -Force "$ProjectRoot\dist" -ErrorAction SilentlyContinue
    Remove-Item -Recurse -Force "$ProjectRoot\__pycache__" -ErrorAction SilentlyContinue
    Get-ChildItem -Path $ProjectRoot -Recurse -Directory -Filter "__pycache__" |
        Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "  Cleaned." -ForegroundColor Green
} else {
    Write-Host "[1/6] Skipping clean (use -Clean to clean first)" -ForegroundColor DarkGray
}

# ── Check Python ─────────────────────────────────────────────────────────
Write-Host "[2/6] Checking Python..." -ForegroundColor Yellow
try {
    $pyVersion = python --version 2>&1
    Write-Host "  $pyVersion" -ForegroundColor Green
} catch {
    Write-Host "  Python not found! Install Python 3.9+ from python.org" -ForegroundColor Red
    exit 1
}

# ── Virtual Environment ──────────────────────────────────────────────────
$venvPath = "$ProjectRoot\build-venv"

if (-not $SkipVenv) {
    Write-Host "[3/6] Setting up build environment..." -ForegroundColor Yellow
    if (-not (Test-Path $venvPath)) {
        python -m venv $venvPath
        Write-Host "  Created virtual environment" -ForegroundColor Green
    }
    & "$venvPath\Scripts\Activate.ps1"
    Write-Host "  Activated build-venv" -ForegroundColor Green
} else {
    Write-Host "[3/6] Skipping venv (using current Python)" -ForegroundColor DarkGray
}

# ── Install Dependencies ─────────────────────────────────────────────────
Write-Host "[4/6] Installing build dependencies..." -ForegroundColor Yellow
python -m pip install --upgrade pip --quiet 2>$null
pip install pyinstaller --quiet 2>$null

# Install project requirements
$reqFile = "$ProjectRoot\requirements.txt"
if (Test-Path $reqFile) {
    pip install -r $reqFile --quiet 2>$null
    Write-Host "  Installed requirements.txt" -ForegroundColor Green
}

# Core deps
pip install anthropic python-dotenv --quiet 2>$null
Write-Host "  Dependencies ready" -ForegroundColor Green

# ── Build Executable ─────────────────────────────────────────────────────
Write-Host "[5/6] Building standalone executable..." -ForegroundColor Yellow
Write-Host "  This may take 1-3 minutes..." -ForegroundColor DarkGray
Write-Host ""

$specFile = "$ProjectRoot\zai-coder.spec"
if (-not (Test-Path $specFile)) {
    Write-Host "  Spec file not found: $specFile" -ForegroundColor Red
    exit 1
}

pyinstaller $specFile `
    --distpath "$ProjectRoot\dist" `
    --workpath "$ProjectRoot\build" `
    --noconfirm `
    --clean

Write-Host ""

# ── Check Output ─────────────────────────────────────────────────────────
Write-Host "[6/6] Verifying build output..." -ForegroundColor Yellow
$exePath = "$ProjectRoot\dist\zai-coder.exe"

if (Test-Path $exePath) {
    $size = (Get-Item $exePath).Length / 1MB
    $sizeStr = "{0:N1} MB" -f $size
    Write-Host ""
    Write-Host "  Build successful!" -ForegroundColor Green
    Write-Host "  Output: dist\zai-coder.exe ($sizeStr)" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Quick test:" -ForegroundColor DarkGray
    & $exePath --version
    Write-Host ""
} else {
    Write-Host "  Build failed — dist\zai-coder.exe not found" -ForegroundColor Red
    exit 1
}

# ── NSIS Installer (optional) ────────────────────────────────────────────
if ($Installer) {
    Write-Host "  Building NSIS installer..." -ForegroundColor Yellow
    $nsisPath = Get-ItemProperty -Path "HKLM:\SOFTWARE\NSIS" -ErrorAction SilentlyContinue

    if ($nsisPath -and (Test-Path "$($nsisPath.'(default)')\makensis.exe")) {
        $makensis = "$($nsisPath.'(default)')\makensis.exe"
        & $makensis "$ProjectRoot\installer.nsi"
        if (Test-Path "$ProjectRoot\dist\ZAI-Coder-$Version-Setup.exe") {
            Write-Host "  Installer created: dist\ZAI-Coder-$Version-Setup.exe" -ForegroundColor Green
        }
    } else {
        # Try common install paths
        $nsisExe = @(
            "C:\Program Files (x86)\NSIS\makensis.exe",
            "C:\Program Files\NSIS\makensis.exe"
        ) | Where-Object { Test-Path $_ } | Select-Object -First 1

        if ($nsisExe) {
            & $nsisExe "$ProjectRoot\installer.nsi"
            if (Test-Path "$ProjectRoot\dist\ZAI-Coder-$Version-Setup.exe") {
                Write-Host "  Installer created: dist\ZAI-Coder-$Version-Setup.exe" -ForegroundColor Green
            }
        } else {
            Write-Host "  NSIS not found. Install from https://nsis.sourceforge.io" -ForegroundColor Yellow
            Write-Host "  Then run: makensis installer.nsi" -ForegroundColor Yellow
        }
    }
}

# ── Summary ──────────────────────────────────────────────────────────────
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Build Complete" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Executable: dist\zai-coder.exe" -ForegroundColor White
Write-Host ""
Write-Host "  Usage:" -ForegroundColor DarkGray
Write-Host "    set ANTHROPIC_API_KEY=sk-ant-..." -ForegroundColor DarkGray
Write-Host "    dist\zai-coder.exe -p ""Write a hello world""" -ForegroundColor DarkGray
Write-Host "    dist\zai-coder.exe --tui" -ForegroundColor DarkGray
Write-Host "    dist\zai-coder.exe --help" -ForegroundColor DarkGray
Write-Host ""
