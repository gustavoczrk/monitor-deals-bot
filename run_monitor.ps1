[CmdletBinding()]
param(
    [switch]$ValidateOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectDirectory = $PSScriptRoot
$pythonPath = Join-Path $projectDirectory ".venv\Scripts\python.exe"
$mainPath = Join-Path $projectDirectory "main.py"
$logDirectory = Join-Path $projectDirectory "logs"
$logPath = Join-Path $logDirectory "monitor-deals.log"
$backupLogPath = "$logPath.1"
$maximumLogSize = 5MB

function Assert-RunnerConfiguration {
    if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
        throw "Python do ambiente virtual nao encontrado em: $pythonPath"
    }
    if (-not (Test-Path -LiteralPath $mainPath -PathType Leaf)) {
        throw "Arquivo principal nao encontrado em: $mainPath"
    }
}

function Get-UserNtfyTopic {
    $value = [Environment]::GetEnvironmentVariable("NTFY_TOPIC", "User")
    if ([string]::IsNullOrWhiteSpace($value)) {
        throw (
            "NTFY_TOPIC nao esta configurada no ambiente do usuario. " +
            "Execute .\setup_scheduler.ps1 primeiro."
        )
    }
    return $value
}

if ($ValidateOnly) {
    try {
        Assert-RunnerConfiguration
        $topic = Get-UserNtfyTopic
        $topic = $null
        Write-Output "Configuracao do runner valida."
        Write-Output "Python: $pythonPath"
        Write-Output "Script: $mainPath"
        Write-Output "Diretorio de trabalho: $projectDirectory"
        Write-Output "NTFY_TOPIC: configurada no ambiente do usuario (valor oculto)"
        exit 0
    }
    catch {
        Write-Error $_.Exception.Message
        exit 1
    }
}

New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
if (
    (Test-Path -LiteralPath $logPath -PathType Leaf) -and
    (Get-Item -LiteralPath $logPath).Length -ge $maximumLogSize
) {
    Move-Item -LiteralPath $logPath -Destination $backupLogPath -Force
}

function Write-OperationalLog {
    param([string]$Message)

    Add-Content -LiteralPath $logPath -Value $Message -Encoding UTF8
}

$exitCode = 1
$locationChanged = $false
Write-OperationalLog "[$(Get-Date -Format o)] Inicio"

try {
    Assert-RunnerConfiguration
    $topic = Get-UserNtfyTopic
    $env:NTFY_TOPIC = $topic
    $topic = $null

    Push-Location -LiteralPath $projectDirectory
    $locationChanged = $true
    & $pythonPath $mainPath 2>&1 | ForEach-Object {
        Write-OperationalLog $_.ToString()
    }
    $exitCode = $LASTEXITCODE
    Write-OperationalLog "Codigo de saida: $exitCode"
}
catch {
    Write-OperationalLog "Erro: $($_.Exception.Message)"
    Write-OperationalLog "Codigo de saida: 1"
    $exitCode = 1
}
finally {
    if ($locationChanged) {
        Pop-Location
    }
    Remove-Item Env:NTFY_TOPIC -ErrorAction SilentlyContinue
    Write-OperationalLog "[$(Get-Date -Format o)] Fim"
}

exit $exitCode
