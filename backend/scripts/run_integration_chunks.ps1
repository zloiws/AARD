# Run integration tests in controlled chunks, excluding real_llm
Param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

 $root = Split-Path -Parent $MyInvocation.MyCommand.Definition
 Push-Location $root
 $base = Resolve-Path (Join-Path $root "..")

# Ensure reports and logs dirs
New-Item -ItemType Directory -Path ../reports -Force | Out-Null
New-Item -ItemType Directory -Path ../logs -Force | Out-Null

$patterns = @(
  "test_phase3_*",
  "test_phase4_*",
  "test_agent_*",
  "test_planning_*",
  "test_prompt_*",
  "test_model_*",
  "test_*"
)

$i = 0
$summary = @()
foreach ($p in $patterns) {
  $i++
  $xml = "../reports/integration_chunk_$i.xml"
  $log = "../logs/integration_chunk_$i.log"
  Write-Host ("Running chunk {0}: pattern = {1}" -f $i, $p)
  $cmd = "python -m pytest tests/integration/$p -m `"not real_llm`" -q --junitxml=$xml"
  Write-Host ("Command: {0}" -f $cmd)
  # Expand matching files for the pattern
  $searchPath = Join-Path $base "tests/integration"
  $files = Get-ChildItem -Path $searchPath -Recurse -Include "$p*.py" -File | ForEach-Object { $_.FullName }
  $filesArray = @($files)
  $count = $filesArray.Count
  if ($count -eq 0) {
    Write-Host ("No files found for pattern {0}, skipping chunk {1}" -f $p, $i)
    $exit = 0
    $failed = $false
    $summary += [PSCustomObject]@{Chunk=$i;Pattern=$p;ExitCode=$exit;HasFailed=$failed;Log=$log;Xml=$xml}
    continue
  }
  Write-Host ("Found {0} files for pattern {1}" -f $count, $p)
  & python -m pytest $filesArray -m "not real_llm" -q --junitxml=$xml > $log 2>&1
  $exit = $LASTEXITCODE
  $failed = Select-String -Path $log -Pattern "FAILED" -SimpleMatch -Quiet
  $summary += [PSCustomObject]@{Chunk=$i;Pattern=$p;ExitCode=$exit;HasFailed=$failed;Log=$log;Xml=$xml}
}

Pop-Location

Write-Host "Summary:"
$summary | Format-Table -AutoSize

# return non-zero if any chunk had failures (so CI can detect)
if ($summary | Where-Object {$_.HasFailed}) {
  exit 1
} else {
  exit 0
}


