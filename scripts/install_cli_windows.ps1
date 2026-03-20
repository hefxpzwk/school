param(
  [Parameter(Mandatory = $false)]
  [string]$SourceBinary = ".\neis-cli-windows-latest.exe"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -Path $SourceBinary -PathType Leaf)) {
  throw "Binary not found: $SourceBinary"
}

$targetDir = Join-Path $env:LOCALAPPDATA "Programs\neis-cli"
$targetExe = Join-Path $targetDir "neis-cli.exe"

New-Item -ItemType Directory -Force -Path $targetDir | Out-Null
Copy-Item -Path $SourceBinary -Destination $targetExe -Force

$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if (-not $userPath) {
  $userPath = ""
}

$pathEntries = $userPath -split ";" | Where-Object { $_ -ne "" }
if ($pathEntries -notcontains $targetDir) {
  $newPath = if ($userPath.TrimEnd(";") -eq "") { $targetDir } else { "$userPath;$targetDir" }
  [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
  Write-Output "Added to user PATH: $targetDir"
} else {
  Write-Output "PATH already includes: $targetDir"
}

Write-Output "Installed: $targetExe"
Write-Output "Open a new PowerShell window, then run: neis-cli meals"
