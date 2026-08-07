[CmdletBinding()]
param(
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$taskName = "Monitor Deals Bot"
$projectDirectory = $PSScriptRoot
$runnerPath = Join-Path $projectDirectory "run_monitor.ps1"
$pythonPath = Join-Path $projectDirectory ".venv\Scripts\python.exe"
$powerShellPath = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
$currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$actionArguments = (
    '-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass ' +
    '-File "{0}"' -f $runnerPath
)

if (-not (Test-Path -LiteralPath $runnerPath -PathType Leaf)) {
    throw "Runner nao encontrado em: $runnerPath"
}
if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
    throw "Python do ambiente virtual nao encontrado em: $pythonPath"
}
if (-not (Test-Path -LiteralPath $powerShellPath -PathType Leaf)) {
    throw "Windows PowerShell nao encontrado em: $powerShellPath"
}

if ($DryRun) {
    Write-Output "DryRun: nenhuma variavel ou tarefa sera criada ou alterada."
    Write-Output "Nome: $taskName"
    Write-Output "Usuario: $currentUser"
    Write-Output "Executavel: $powerShellPath"
    Write-Output "Argumentos: $actionArguments"
    Write-Output "Diretorio de trabalho: $projectDirectory"
    Write-Output "Frequencia: a cada 30 minutos"
    Write-Output "Multiplas instancias: IgnoreNew"
    Write-Output "Iniciar quando disponivel: sim"
    Write-Output "Logon: usuario conectado, sem senha armazenada"
    Write-Output "NTFY_TOPIC: nao lida nem exibida no DryRun"
    exit 0
}

Import-Module ScheduledTasks -ErrorAction Stop

$action = New-ScheduledTaskAction `
    -Execute $powerShellPath `
    -Argument $actionArguments `
    -WorkingDirectory $projectDirectory
$trigger = New-ScheduledTaskTrigger `
    -Once `
    -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Minutes 30)
$settings = New-ScheduledTaskSettingsSet `
    -MultipleInstances IgnoreNew `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries
$principal = New-ScheduledTaskPrincipal `
    -UserId $currentUser `
    -LogonType Interactive `
    -RunLevel Limited

$secureTopic = Read-Host "Informe o topico ntfy" -AsSecureString
$topicPointer = [IntPtr]::Zero
$topic = $null
try {
    $topicPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR(
        $secureTopic
    )
    $topic = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($topicPointer)
    if ([string]::IsNullOrWhiteSpace($topic)) {
        throw "O topico ntfy nao pode estar vazio."
    }
    [Environment]::SetEnvironmentVariable("NTFY_TOPIC", $topic, "User")
}
finally {
    $topic = $null
    if ($topicPointer -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($topicPointer)
    }
}

Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "Monitora precos de monitores a cada 30 minutos." `
    -Force | Out-Null

Write-Output "Tarefa '$taskName' instalada com sucesso."
Write-Output "O valor de NTFY_TOPIC foi armazenado no ambiente do usuario e nao foi exibido."
