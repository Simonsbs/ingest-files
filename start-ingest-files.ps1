param(
    [string]$ImageName     = "simongpt-ingest-files",
    [string]$ContainerName = "ingest-files",
    [string]$WatchPath     = "D:\Projects\SimonGPT\services\ingest-files\files",
    [int]   $Port          = 8081
)

# Where the script lives
$scriptDir = $PSScriptRoot

# 1) Resolve & normalize your host folder path
try {
    $hostPath = (Resolve-Path -Path $WatchPath).ProviderPath
} catch {
    Write-Error "❌ WatchPath '$WatchPath' does not exist."
    exit 1
}
# Docker on Windows wants forward-slashes
$watchMount = $hostPath.TrimEnd('\') -replace '\\', '/'

# 2) Build the image and bail out on failure
Write-Host "🐳 Building Docker image '$ImageName' from $scriptDir…"
Push-Location $scriptDir
docker build -t $ImageName .
if ($LASTEXITCODE -ne 0) {
    Write-Error "❌ Docker build failed. Aborting."
    exit 1
}
Pop-Location

# 3) Tear down any old container
Write-Host "🛑 Removing existing container (if any)…"
docker rm -f $ContainerName 2>$null

# 4) Ensure .env is next to this script
$envFile = Join-Path $scriptDir ".env"
if (-not (Test-Path $envFile)) {
    Write-Error "❌ .env file not found at $envFile"
    exit 1
}

# 5) Run the container
Write-Host "🚀 Starting container '$ContainerName'…"
$dockerArgs = @(
    "run", "--rm", "-d",
    "--name", $ContainerName,
    "-v", "${watchMount}:/data/incoming",
    "--env-file", $envFile,
    "-p", "$Port`:8081",
    $ImageName
)
docker @dockerArgs
if ($LASTEXITCODE -ne 0) {
    Write-Error "❌ Failed to start container."
    exit 1
}

Write-Host "✅ Ingest-files service is up! Watching host path: $hostPath"
