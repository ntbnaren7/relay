$ErrorActionPreference = "Stop"

$Repo = "ntbnaren7/relay"
$InstallDir = "$env:USERPROFILE\.relay\bin"

if (!(Test-Path -Path $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir | Out-Null
}

$AssetName = "relay-windows-x64.exe"
$LatestUrl = "https://github.com/$Repo/releases/latest/download/$AssetName"
$TargetFile = "$InstallDir\relay.exe"

Write-Host "⬇️ Downloading Relay for Windows-x64..."
Invoke-WebRequest -Uri $LatestUrl -OutFile $TargetFile

Write-Host "🎉 Relay installed successfully to $TargetFile"

$UserPath = [Environment]::GetEnvironmentVariable("PATH", "User")
if ($UserPath -notlike "*$InstallDir*") {
    $NewPath = "$UserPath;$InstallDir"
    [Environment]::SetEnvironmentVariable("PATH", $NewPath, "User")
    Write-Host "✅ Added $InstallDir to your PATH. Please restart your terminal to run 'relay' directly!"
} else {
    Write-Host "🚀 Run 'relay' to get started!"
}
