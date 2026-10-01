param([string]$Compiler = (Join-Path $PSScriptRoot 'build-tools/inno/ISCC.exe'))
$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $Compiler)) { throw 'Install Inno Setup 6 and provide -Compiler with the ISCC.exe path.' }
& (Join-Path $PSScriptRoot 'build.ps1')
& $Compiler (Join-Path $PSScriptRoot 'installer.iss')
if ($LASTEXITCODE -ne 0) { throw 'Installer build failed.' }
