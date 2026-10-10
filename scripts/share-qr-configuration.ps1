param(
    [Parameter(Mandatory=$true)][ValidateSet('Export','Import')][string]$Mode,
    [string]$SharedFile
)
$ErrorActionPreference='Stop'
$repo=Split-Path $PSScriptRoot -Parent
$privateDir=Join-Path $repo '.tools'
$localPath=Join-Path $repo 'backend/SolarTrading.Api/appsettings.Local.json'
if (!$SharedFile) { $SharedFile=Join-Path $privateDir 'shared-qr-settings.json' }
elseif (![IO.Path]::IsPathRooted($SharedFile)) { $SharedFile=Join-Path $repo $SharedFile }
$SharedFile=[IO.Path]::GetFullPath($SharedFile)
# Shared credentials stay under the repository's ignored private directory.
$privatePrefix=[IO.Path]::GetFullPath($privateDir).TrimEnd('\')+'\'
if (!$SharedFile.StartsWith($privatePrefix,[StringComparison]::OrdinalIgnoreCase)) {
    throw 'Keep the shared settings file under this repository''s ignored .tools directory.'
}
if (!(Test-Path -LiteralPath $localPath)) { throw 'Existing private appsettings.Local.json is required.' }
$local=Get-Content -LiteralPath $localPath -Raw | ConvertFrom-Json
$base=Get-Content -LiteralPath (Join-Path $repo 'backend/SolarTrading.Api/appsettings.json') -Raw | ConvertFrom-Json
function Validate-SharedSettings($settings) {
    if ([Text.Encoding]::UTF8.GetByteCount([string]$settings.Qr.Key) -lt 32) {
        throw 'The QR signing key must contain at least 32 bytes.'
    }
    if ([string]::IsNullOrWhiteSpace([string]$settings.Mongo.Database) -or
        [string]$settings.Mongo.ConnectionString -notmatch '^mongodb(\+srv)?://') {
        throw 'A MongoDB connection string and database name are required.'
    }
    # A loopback database on two different laptops does not share booking records.
    $authority=(([string]$settings.Mongo.ConnectionString -replace '^mongodb(\+srv)?://','') -split '[/?]',2)[0]
    $hosts=($authority -split '@')[-1]
    if ($hosts -match '(^|,)(localhost|127\.0\.0\.1|\[::1\])(:\d+)?($|,)') {
        throw 'Two laptops require one shared MongoDB endpoint; a localhost database is not supported for this export/import.'
    }
}
if ($Mode -eq 'Export') {
    if (Test-Path -LiteralPath $SharedFile) { throw 'Shared settings file already exists; choose a new filename under .tools.' }
    $shared=@{
        Version=1
        Mongo=@{
            ConnectionString=$local.Mongo.ConnectionString
            Database=$(if ($local.Mongo.Database) { $local.Mongo.Database } else { $base.Mongo.Database })
        }
        Qr=@{Key=$local.Qr.Key}
    }
    Validate-SharedSettings $shared
    New-Item -ItemType Directory -Path (Split-Path $SharedFile -Parent) -Force | Out-Null
    [IO.File]::WriteAllText($SharedFile,($shared | ConvertTo-Json -Depth 5),[Text.UTF8Encoding]::new($false))
    Write-Output 'Private shared QR/Mongo settings exported. Transfer this file directly to the other laptop; do not upload it to Git or chat.'
} else {
    $shared=Get-Content -LiteralPath $SharedFile -Raw | ConvertFrom-Json
    if ($shared.Version -ne 1) { throw 'Unsupported shared settings version.' }
    Validate-SharedSettings $shared
    New-Item -ItemType Directory -Path $privateDir -Force | Out-Null
    $backup=Join-Path $privateDir ('local-config-before-qr-import-'+[Guid]::NewGuid().ToString('N')+'.json')
    Copy-Item -LiteralPath $localPath -Destination $backup
    if (!$local.Mongo) { $local | Add-Member NoteProperty Mongo ([pscustomobject]@{}) }
    if (!$local.Qr) { $local | Add-Member NoteProperty Qr ([pscustomobject]@{}) }
    $local.Mongo | Add-Member NoteProperty ConnectionString $shared.Mongo.ConnectionString -Force
    $local.Mongo | Add-Member NoteProperty Database $shared.Mongo.Database -Force
    $local.Qr | Add-Member NoteProperty Key $shared.Qr.Key -Force
    [IO.File]::WriteAllText($localPath,($local | ConvertTo-Json -Depth 20),[Text.UTF8Encoding]::new($false))
    Write-Output 'Shared QR/Mongo settings imported; original private configuration backed up under .tools. Run sync-iis-configuration.ps1 as administrator on this IIS laptop.'
}
$sha=[Security.Cryptography.SHA256]::Create()
try {
    $fingerprint=[BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes([string]$shared.Qr.Key))).Replace('-','').ToLowerInvariant()
    Write-Output ('QR key SHA256 fingerprint: '+$fingerprint)
} finally { $sha.Dispose() }
