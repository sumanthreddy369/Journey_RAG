# Creates ignored local credentials, starts loopback PostgreSQL, and migrates it.
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$credentialsPath = Join-Path (Get-Location) '.env.progress'
if (-not (Test-Path -LiteralPath $credentialsPath)) {
    $password = [guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N')
    @("JOURNEY_POSTGRES_PASSWORD=$password", "JOURNEY_DATABASE_URL=postgresql+psycopg://journey:${password}@127.0.0.1:5435/journey") | Set-Content -LiteralPath $credentialsPath
}
foreach ($line in Get-Content -LiteralPath $credentialsPath) {
    $parts = $line.Split('=', 2)
    if ($parts.Length -eq 2) { [Environment]::SetEnvironmentVariable($parts[0], $parts[1], 'Process') }
}
$docker = Get-Command docker -ErrorAction SilentlyContinue
if ($docker) { $dockerPath = $docker.Source }
else { $dockerPath = 'C:\Program Files\Docker\Docker\resources\bin\docker.exe' }
$env:PATH = (Split-Path $dockerPath -Parent) + ';' + $env:PATH
& $dockerPath compose -p journey-progress --env-file $credentialsPath -f compose.progress.yaml up -d --wait
if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL startup failed.' }
& .\venv\Scripts\python.exe -m alembic upgrade head
if ($LASTEXITCODE -ne 0) { throw 'Progress migration failed.' }
Write-Host 'Local progress database is ready on 127.0.0.1:5435. Start the API in this shell.'
