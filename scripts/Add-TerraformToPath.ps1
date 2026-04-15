<#
.SYNOPSIS
  WinGet often installs Terraform without putting it on PATH. This script adds the
  WinGet package folder that contains terraform.exe to your *user* PATH (one-time).
#>
$ErrorActionPreference = "Stop"
$packagesRoot = Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Packages"
$dirs = Get-ChildItem -Path $packagesRoot -Directory -Filter "Hashicorp.Terraform*" -ErrorAction SilentlyContinue
$terraformDir = $null
foreach ($d in $dirs) {
    $exe = Join-Path $d.FullName "terraform.exe"
    if (Test-Path $exe) {
        $terraformDir = $d.FullName
        break
    }
}
if (-not $terraformDir) {
    Write-Host "Could not find terraform.exe under $packagesRoot"
    Write-Host "Install with: winget install --id Hashicorp.Terraform -e --accept-package-agreements"
    exit 1
}

$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -like "*$terraformDir*") {
    Write-Host "Already on user PATH: $terraformDir"
} else {
    $newPath = "$terraformDir;$userPath"
    [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
    Write-Host "Added to user PATH: $terraformDir"
}

# Current session only (so you can run terraform immediately without closing window):
$env:Path = "$terraformDir;$env:Path"
Write-Host ""
& "$terraformDir\terraform.exe" -version
Write-Host ""
Write-Host "Close and reopen PowerShell if 'terraform' still fails in other windows."
