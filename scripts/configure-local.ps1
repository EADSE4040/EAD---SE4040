param([string]$AdminEmail = 'admin@solara.local', [string]$MongoUrl = 'mongodb://127.0.0.1:27018/?replicaSet=rs0')
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$configPath = Join-Path $repo 'backend/SolarTrading.Api/appsettings.Local.json'
if (Test-Path -LiteralPath $configPath) { throw 'Local configuration already exists. Edit it explicitly instead of replacing secrets.' }
function New-Secret {
    $bytes = New-Object byte[] 48
    $rng = [Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($bytes); return [Convert]::ToBase64String($bytes) } finally { $rng.Dispose() }
}
$password = New-Secret
$config = @{ Mongo = @{ConnectionString=$MongoUrl}; Jwt=@{Key=(New-Secret)}; Qr=@{Key=(New-Secret)}; Bootstrap=@{Email=$AdminEmail;Password=$password} }
[IO.File]::WriteAllText($configPath, ($config | ConvertTo-Json -Depth 5))
$privateDir = Join-Path $repo '.tools'
New-Item -ItemType Directory -Path $privateDir -Force | Out-Null
[IO.File]::WriteAllText((Join-Path $privateDir 'dev-credentials.json'), (@{Email=$AdminEmail;Password=$password} | ConvertTo-Json))
Write-Output 'Local secrets configured. Initial administrator credentials are in .tools/dev-credentials.json (excluded from Git).'
