# Installs the call test app on a phone connected by USB (USB debugging on).
# Installing from the laptop is "offline sideloading", which Play Protect's fraud protection allows;
# downloading the APK in a browser is blocked for apps that use the accessibility permission.
$adb = "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe"
$apk = Join-Path $PSScriptRoot "app\build\outputs\apk\debug\app-debug.apk"
& $adb start-server | Out-Null
$devices = (& $adb devices) | Select-String "\tdevice$"
if (-not $devices) {
    Write-Host "No phone found. Connect it by USB, turn on USB debugging, and tap 'Allow' on the phone." -ForegroundColor Yellow
    & $adb devices
    exit 1
}
Write-Host "Installing on: $($devices -join ', ')"
& $adb uninstall ai.scamsentinel.probe 2>$null | Out-Null      # an old copy installed from the browser
& $adb install -r $apk
if ($LASTEXITCODE -eq 0) { & $adb shell monkey -p ai.scamsentinel.probe 1 | Out-Null; Write-Host "Installed and opened." -ForegroundColor Green }
