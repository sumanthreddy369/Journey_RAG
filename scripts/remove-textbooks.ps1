param(
    [Parameter(Mandatory = $true, Position = 0, ValueFromRemainingArguments = $true)]
    [string[]]$Paths
)

$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
& .\venv\Scripts\python.exe textbook_ingest.py --remove @Paths
if ($LASTEXITCODE -ne 0) { throw 'Textbook removal failed.' }
