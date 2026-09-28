param([Parameter(Mandatory=$true)][ValidatePattern('^IT[0-9]+$')][string]$ITNumber)
$ErrorActionPreference='Stop'
$repo=Split-Path $PSScriptRoot -Parent
$artifactDir=Join-Path $repo 'artifacts'
New-Item -ItemType Directory -Path $artifactDir -Force | Out-Null
$staging=Join-Path $artifactDir ('submission-'+[Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $staging | Out-Null
Push-Location $repo
try {
    $files=@(& git ls-files)
    if ($LASTEXITCODE -ne 0) { throw 'Unable to enumerate tracked submission files.' }
    foreach($relative in $files) {
        if($relative -match '(^|/)(\.tools|node_modules|bin|obj|build|dist|\.git)(/|$)' -or $relative -match 'appsettings\.Local\.json$|maps\.properties$|local\.properties$|\.env$') { continue }
        $source=Join-Path $repo $relative
        $destination=Join-Path $staging $relative
        New-Item -ItemType Directory -Path (Split-Path $destination -Parent) -Force | Out-Null
        Copy-Item -LiteralPath $source -Destination $destination
    }
    & node (Join-Path $repo 'scripts/generate-report.mjs')
    if ($LASTEXITCODE -ne 0) { throw 'Report generation failed.' }
    Copy-Item -LiteralPath (Join-Path $artifactDir 'report-with-source.md') -Destination (Join-Path $staging 'report-with-source.md')
    $zip=Join-Path $artifactDir ($ITNumber+'.zip')
    if(Test-Path -LiteralPath $zip){throw 'A submission ZIP already exists; choose explicitly whether to replace it.'}
    Compress-Archive -Path (Join-Path $staging '*') -DestinationPath $zip
    Write-Output ('Submission archive created: '+$zip)
    Write-Output 'Verify report formatting, member contributions, screenshots, video link, and IIS/device evidence before submitting.'
} finally { Pop-Location }
