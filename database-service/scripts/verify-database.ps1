$ErrorActionPreference = "Stop"

$ContainerName = "knowledge-assistant-db"

$DatabaseName = if ($env:POSTGRES_DB) {
    $env:POSTGRES_DB
} else {
    "knowledge_assistant"
}

$DatabaseUser = if ($env:POSTGRES_USER) {
    $env:POSTGRES_USER
} else {
    "knowledge_admin"
}

$ProjectRoot = Resolve-Path (
    Join-Path $PSScriptRoot "..\.."
)

$TestDirectory = Join-Path `
    $ProjectRoot `
    "database-service\tests"

if (-not (Test-Path $TestDirectory)) {
    throw "Database test directory not found: $TestDirectory"
}

$Running = docker inspect `
    -f "{{.State.Running}}" `
    $ContainerName `
    2>$null

if ($Running -ne "true") {
    throw "Container '$ContainerName' is not running."
}

Write-Host "Copying database tests into the container..."

docker exec $ContainerName `
    rm -rf /tmp/knowledge-assistant-tests

docker cp `
    $TestDirectory `
    "${ContainerName}:/tmp/knowledge-assistant-tests"

$Tests = @(
    "01-health-check.sql",
    "02-schema-validation.sql",
    "03-crud-test.sql"
)

foreach ($Test in $Tests) {
    Write-Host ""
    Write-Host "Running $Test..."

    docker exec `
        -e PGPASSWORD=$env:POSTGRES_PASSWORD `
        $ContainerName `
        psql `
        -v ON_ERROR_STOP=1 `
        -U $DatabaseUser `
        -d $DatabaseName `
        -f "/tmp/knowledge-assistant-tests/$Test"

    if ($LASTEXITCODE -ne 0) {
        throw "Database test failed: $Test"
    }
}

Write-Host ""
Write-Host "All database verification tests passed."