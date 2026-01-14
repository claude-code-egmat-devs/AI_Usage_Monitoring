# Claude Code Monitor - Windows Setup Script
# Run this script to set up the usage reporter on a Windows machine

Write-Host "=" * 60
Write-Host "Claude Code Monitor - Windows Setup"
Write-Host "=" * 60

# Check Python
Write-Host "`nChecking Python..."
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Python not found. Please install Python 3.9+" -ForegroundColor Red
    exit 1
}
Write-Host "Found: $pythonVersion"

# Get script directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Create virtual environment if it doesn't exist
$venvPath = Join-Path $scriptDir "venv"
if (-not (Test-Path $venvPath)) {
    Write-Host "`nCreating virtual environment..."
    python -m venv $venvPath
}

# Activate and install dependencies
Write-Host "`nInstalling dependencies..."
& "$venvPath\Scripts\pip.exe" install -r "$scriptDir\requirements.txt"

# Check if .env exists
$envPath = Join-Path $scriptDir "config\.env"
if (-not (Test-Path $envPath)) {
    Write-Host "`nWARNING: .env file not found" -ForegroundColor Yellow
    Write-Host "Please copy config\.env.example to config\.env and configure it"
}

# Test the usage reader
Write-Host "`nTesting usage reader..."
& "$venvPath\Scripts\python.exe" "$scriptDir\lib\claude_usage_reader.py"

Write-Host "`n" + "=" * 60
Write-Host "Setup Complete!"
Write-Host "=" * 60

Write-Host "`nTo run the reporter manually:"
Write-Host "  .\venv\Scripts\python.exe services\usage_reporter.py --dry-run"

Write-Host "`nTo set up scheduled task (run every 4 hours):"
Write-Host @"
  `$action = New-ScheduledTaskAction -Execute "$venvPath\Scripts\python.exe" -Argument "$scriptDir\services\usage_reporter.py"
  `$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Hours 4)
  Register-ScheduledTask -TaskName "ClaudeCodeMonitor" -Action `$action -Trigger `$trigger -Description "Claude Code usage reporter"
"@
