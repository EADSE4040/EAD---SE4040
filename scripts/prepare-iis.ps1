# Prepare artifacts and Microsoft's verified installer without administrator privileges.
$ErrorActionPreference='Stop'
$repo=Split-Path $PSScriptRoot -Parent
& (Join-Path $PSScriptRoot 'publish.ps1') -LocalIis
$metadata=Invoke-RestMethod 'https://builds.dotnet.microsoft.com/dotnet/release-metadata/10.0/releases.json'
$release=$metadata.releases | Where-Object { $_.'release-version' -eq '10.0.12' } | Select-Object -First 1
$file=$release.'aspnetcore-runtime'.files | Where-Object { $_.name -eq 'dotnet-hosting-win.exe' } | Select-Object -First 1
if (!$file -or $file.url -notlike 'https://builds.dotnet.microsoft.com/*') { throw 'Official installer metadata was not found.' }
$installer=Join-Path $repo '.tools/dotnet-hosting-10.0.12-win.exe'
if (!(Test-Path -LiteralPath $installer)) { Invoke-WebRequest -Uri $file.url -OutFile $installer }
if ((Get-FileHash -LiteralPath $installer -Algorithm SHA512).Hash -ne $file.hash) { throw 'Installer SHA512 verification failed.' }
$signature=Get-AuthenticodeSignature -LiteralPath $installer
if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'O=Microsoft Corporation') { throw 'Installer Microsoft signature verification failed.' }
Write-Output 'Local IIS artifacts and the SHA512/signature-verified Hosting Bundle are ready. Installation requires administrator Windows PowerShell.'
