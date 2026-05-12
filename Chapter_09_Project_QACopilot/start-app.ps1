$projectRoot = "C:\Users\surya\Documents\AI Tester\QA Copilot\qa-copilot"
$logFile = Join-Path $projectRoot "app.log"

$env:PYTHONPATH = $projectRoot
$streamlit = Join-Path $projectRoot ".venv\Scripts\streamlit.exe"

$proc = Start-Process -FilePath $streamlit -ArgumentList "run","src/ui/app.py","--server.headless","true","--server.port","8501" -PassThru -WindowStyle Hidden

Write-Host "QA Copilot started (PID: $($proc.Id))"
Write-Host "Log: $logFile"

while (-not $proc.HasExited) {
    Start-Sleep -Seconds 30
    if (-not (Test-Path "http://localhost:8501")) {
        Write-Host "Checking connection..."
    }
}

if ($proc.HasExited) {
    Write-Host "Process exited with code: $($proc.ExitCode)"
}