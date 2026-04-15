# Dot-source this file to set JAVA_HOME for the current PowerShell session:
#   . .\scripts\setup_java_env.ps1
$ErrorActionPreference = "Stop"
$candidates = @(
    "${env:ProgramFiles}\Eclipse Adoptium\jdk-*"
    "${env:ProgramFiles}\Java\jdk-*"
    "${env:ProgramFiles}\Microsoft\jdk-*"
)
$jdk = $null
foreach ($pat in $candidates) {
    $found = Get-ChildItem -Path $pat -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($found -and (Test-Path (Join-Path $found.FullName "bin\java.exe"))) {
        $jdk = $found.FullName
        break
    }
}
if (-not $jdk) {
    Write-Host "No JDK found under Program Files. Install JDK 17, e.g.:"
    Write-Host "  winget install EclipseAdoptium.Temurin.17.JDK"
    exit 1
}
$env:JAVA_HOME = $jdk
$env:Path = "$(Join-Path $jdk 'bin');$env:Path"
Write-Host "JAVA_HOME=$env:JAVA_HOME"
& java -version
