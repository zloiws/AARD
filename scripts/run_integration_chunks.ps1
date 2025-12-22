param(
    [int] $ChunkSize = 20
)

$base = "backend"
$testDir = Join-Path $base "tests\integration"
$reportsDir = "reports"
$logsDir = "logs"

if (-not (Test-Path $reportsDir)) { New-Item -ItemType Directory -Path $reportsDir | Out-Null }
if (-not (Test-Path $logsDir)) { New-Item -ItemType Directory -Path $logsDir | Out-Null }

Write-Host "Collecting integration test files from $testDir"
$files = Get-ChildItem -Path $testDir -Filter *.py -Recurse | Where-Object { -not $_.PSIsContainer } | Select-Object -ExpandProperty FullName
$total = $files.Count
Write-Host "Found $total files"

if ($total -eq 0) {
    Write-Host "No integration test files found under $testDir"
    exit 0
}

$i = 0
for ($start = 0; $start -lt $total; $start += $ChunkSize) {
    $i++
    $chunk = $files[$start..([Math]::Min($start + $ChunkSize - 1, $total - 1))]
    $listFile = Join-Path $reportsDir "integration_chunk_${i}_files.txt"
    $xmlOut = Join-Path $reportsDir "integration_chunk_${i}.xml"
    $logOut = Join-Path $logsDir "integration_chunk_${i}.log"
    $chunk | Set-Content -Path $listFile -Encoding utf8
    Write-Host "Running chunk $i: $($chunk.Count) files -> $xmlOut"
    $cmd = "python -m pytest -q -m `"not real_llm`" @$listFile --junitxml=$xmlOut"
    Write-Host $cmd
    & python -m pytest -q -m "not real_llm" @($chunk) --junitxml=$xmlOut > $logOut 2>&1
    $exit = $LASTEXITCODE
    Write-Host "Chunk $i completed with exit code $exit; log -> $logOut"
}

Write-Host "All chunks completed."

