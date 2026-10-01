$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$dependencyFolder = Join-Path (Split-Path -Parent $projectRoot) '.build-deps'
$env:PYTHONPATH = $dependencyFolder + ';' + (Join-Path $projectRoot 'libraries/phidgets_lib')
$env:PYINSTALLER_CONFIG_DIR = Join-Path $PSScriptRoot 'build-cache'
Push-Location $projectRoot
try {
    python -m PyInstaller --noconfirm --onefile --windowed --name 'NEAQ Hardware Tester' --distpath HardwareTester/release --workpath HardwareTester/build --specpath HardwareTester --paths libraries/phidgets_lib --collect-all Phidget22 --hidden-import serial.tools.list_ports --add-data 'panel.html;.' --add-data 'config.json;.' HardwareTester/app.py
    if ($LASTEXITCODE -ne 0) { throw 'Executable build failed.' }
    Copy-Item -LiteralPath HardwareTester/config.json -Destination HardwareTester/release/config.json
    Copy-Item -LiteralPath HardwareTester/README.txt -Destination HardwareTester/release/README.txt
    Compress-Archive -Path HardwareTester/release/* -DestinationPath 'HardwareTester/NEAQ Hardware Tester.zip' -Force
} finally {
    Pop-Location
}
