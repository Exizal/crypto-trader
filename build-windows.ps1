param(
    [string]$OutputDirectory = (Join-Path (Split-Path $PSScriptRoot -Parent) 'Crypto Trader AI'),
    [string]$BuildDirectory = (Join-Path $PSScriptRoot 'work\windows-build')
)
$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Force -Path $BuildDirectory | Out-Null
$seedDirectory = Join-Path $PSScriptRoot 'data'
$entryPoint = Join-Path $PSScriptRoot 'trader_desktop.py'
$buildArguments = @('-m','PyInstaller','--noconfirm','--onefile','--windowed','--noupx','--name','Crypto Trader','--distpath',$OutputDirectory,'--workpath',$BuildDirectory,'--specpath',$BuildDirectory)
if (Test-Path -LiteralPath $seedDirectory) { $buildArguments += @('--add-data',"$seedDirectory;seed_data") }
$buildArguments += $entryPoint
python @buildArguments
if ($LASTEXITCODE -ne 0) { throw 'Windows app build failed.' }
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'README.md') -Destination (Join-Path $OutputDirectory 'README.md') -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'docs\guide.tr.md') -Destination (Join-Path $OutputDirectory 'KULLANIM.md') -Force
