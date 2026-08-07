[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$taskName = "Monitor Deals Bot"
Import-Module ScheduledTasks -ErrorAction Stop

$task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($null -eq $task) {
    Write-Output "A tarefa '$taskName' nao esta instalada."
    exit 0
}

Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
Write-Output "Tarefa '$taskName' removida."
Write-Output "state.json, logs e NTFY_TOPIC foram preservados."
