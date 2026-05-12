$projectRoot = "C:\Users\surya\Documents\AI Tester\QA Copilot\qa-copilot"
$logFile = Join-Path $projectRoot "streamlit.log"

$env:PYTHONPATH = $projectRoot
$streamlit = Join-Path $projectRoot ".venv\Scripts\streamlit.exe"

$scriptPath = Join-Path $projectRoot "src\ui\app.py"

$proc = Start-Process -FilePath $streamlit -ArgumentList "run","`"$scriptPath`"","--server.headless","true","--server.port","8501" -PassThru -WorkingDirectory $projectRoot -RedirectStandardOutput $logFile -WindowStyle Normal

Start-Sleep -Seconds 3

if ($proc.HasExited) {
    Write-Host "Process exited with code: $($proc.ExitCode)"
    if (Test-Path $logFile) {
        Get-Content $logFile | Select-Object -Last 20
    }
} else {
    Write-Host "QA Copilot running (PID: $($proc.Id))"
    Write-Host "Access at: http://localhost:8501"
}