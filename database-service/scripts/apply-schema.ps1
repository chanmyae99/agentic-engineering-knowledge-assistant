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

$SchemaDirectory = Join-Path `
    $ProjectRoot `
    "database-service\schema"

if (-not (Test-Path $SchemaDirectory)) {
    throw "Schema directory not found: $SchemaDirectory"
}

Write-Host "Checking PostgreSQL container..."

$Running = docker inspect `
    -f "{{.State.Running}}" `
    $ContainerName `
    2>$null

if ($Running -ne "true") {
    throw "Container '$ContainerName' is not running."
}

Write-Host "Copying schema files into the container..."

docker exec $ContainerName `
    rm -rf /tmp/knowledge-assistant-schema

docker cp `
    $SchemaDirectory `
    "${ContainerName}:/tmp/knowledge-assistant-schema"

Write-Host "Applying database schema..."

docker exec `
    -e PGPASSWORD=$env:POSTGRES_PASSWORD `
    $ContainerName `
    psql `
    -v ON_ERROR_STOP=1 `
    -U $DatabaseUser `
    -d $DatabaseName `
    -f /tmp/knowledge-assistant-schema/05-apply-schema.sql

if ($LASTEXITCODE -ne 0) {
    throw "Database schema application failed."
}

Write-Host ""
Write-Host "Database schema applied successfully."