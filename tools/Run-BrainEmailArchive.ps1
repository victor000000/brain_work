# Run the BRAIN email research archive with the read-only Gmail connector.
# This job never starts the simulation service, opens DuckDB, or submits alphas.
$ErrorActionPreference = 'Stop'

$candidates = @(
    $env:DSH_EMAIL_PYTHON,
    'C:\Users\victo\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe'
)
$python = $candidates | Where-Object { $_ -and (Test-Path -LiteralPath $_) } | Select-Object -First 1
if (-not $python) {
    throw 'No Python interpreter found for the BRAIN email archive.'
}

$script = Join-Path $PSScriptRoot 'brain_email_archive.py'
& $python $script --max-new 40 --prune-non-research
exit $LASTEXITCODE
