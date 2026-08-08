$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$webRoot = Join-Path $projectRoot "apps\web"

if (-not (Test-Path -LiteralPath $python)) {
    throw "Virtual environment not found. Create .venv and install requirements.txt first."
}

$api = Start-Process -FilePath $python `
    -ArgumentList "-m", "backend.main", "--index", "data/structured/vector_index", "--port", "8000" `
    -WorkingDirectory $projectRoot `
    -WindowStyle Hidden `
    -PassThru

try {
    Write-Host "Loading ARLIS index and embedding model..."
    $deadline = (Get-Date).AddMinutes(3)
    $ready = $false
    while ((Get-Date) -lt $deadline) {
        if ($api.HasExited) {
            throw "The ARLIS API stopped during startup (exit code $($api.ExitCode))."
        }
        $client = [Net.Sockets.TcpClient]::new()
        try {
            if ($client.ConnectAsync("127.0.0.1", 8000).Wait(2000) -and $client.Connected) {
                $ready = $true
                break
            }
        }
        catch {
            Start-Sleep -Seconds 2
        }
        finally {
            $client.Dispose()
        }
    }
    if (-not $ready) {
        throw "The ARLIS API did not become ready within 3 minutes."
    }
    Write-Host "API ready. Starting frontend..." -ForegroundColor Green
    Write-Host "Frontend: http://127.0.0.1:5173"
    Write-Host "API:      http://127.0.0.1:8000/api/research"
    Set-Location $webRoot
    & npm.cmd run dev -- --host 127.0.0.1
}
finally {
    if ($api -and -not $api.HasExited) {
        Stop-Process -Id $api.Id
    }
}
