$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $projectRoot '.env'
$examplePath = Join-Path $projectRoot '.env.example'

if (-not (Test-Path -LiteralPath $envPath)) {
    Copy-Item -LiteralPath $examplePath -Destination $envPath
}

$content = [System.IO.File]::ReadAllText($envPath)
$existing = [regex]::Match($content, '(?m)^DEMO_HR_TOKEN=([^\r\n]*)')
if ($existing.Success -and $existing.Groups[1].Value.Trim()) {
    Write-Host 'DEMO_HR_TOKEN already exists in .env; it was not changed.'
    return
}

$bytes = New-Object byte[] 32
$generator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
try {
    $generator.GetBytes($bytes)
} finally {
    $generator.Dispose()
}
$token = [Convert]::ToBase64String($bytes).TrimEnd('=').Replace('+', '-').Replace('/', '_')

if ($existing.Success) {
    $content = ([regex]::new('(?m)^DEMO_HR_TOKEN=[^\r\n]*')).Replace($content, "DEMO_HR_TOKEN=$token", 1)
} else {
    if ($content.Length -gt 0 -and -not $content.EndsWith("`n")) {
        $content += [Environment]::NewLine
    }
    $content += "DEMO_HR_TOKEN=$token" + [Environment]::NewLine
}
[System.IO.File]::WriteAllText($envPath, $content)
Write-Host 'Generated DEMO_HR_TOKEN in .env. Enter this token in the web login:'
Write-Host $token
