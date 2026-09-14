$ErrorActionPreference = "Stop"

$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$review = $PSScriptRoot
$stage = Join-Path $review "chatgpt_review_package_v3"
$zip = Join-Path $review "chatgpt_review_package_v3.zip"

if ((Test-Path $stage) -or (Test-Path $zip)) {
    throw "Review package v3 already exists; use a new version name instead of overwriting it."
}

New-Item -ItemType Directory -Path $stage | Out-Null

$rootFiles = @(
    "README.md",
    "NEXT_ACTIONS.md",
    "environment.yml",
    "requirements.txt",
    "requirements-publication.txt",
    "PUBLICATION_GATE_TERMINAL_RUN.md",
    "completion_status.json",
    "final_archive_manifest.json",
    "paper.pdf",
    "report.pdf"
)
foreach ($file in $rootFiles) {
    $source = Join-Path $root $file
    if (Test-Path $source) {
        Copy-Item -LiteralPath $source -Destination (Join-Path $stage $file)
    }
}

$directoryRules = @(
    @{ Path = "scripts"; Extensions = @(".py", ".cmd") },
    @{ Path = "config"; Extensions = @(".json", ".csv", ".yaml", ".yml") },
    @{ Path = "data\figure_source"; Extensions = @(".csv", ".json", ".md", ".txt", ".geojson", ".parquet") },
    @{ Path = "data\processed"; Extensions = @(".csv", ".json", ".md", ".txt", ".geojson", ".parquet") },
    @{ Path = "figures\main"; Extensions = @(".png", ".pdf") },
    @{ Path = "docs"; Extensions = @(".md", ".json", ".txt") },
    @{ Path = "tests"; Extensions = @(".py") }
)
foreach ($rule in $directoryRules) {
    $directory = $rule.Path
    $source = Join-Path $root $directory
    if (-not (Test-Path $source)) {
        continue
    }
    $destination = Join-Path $stage $directory
    New-Item -ItemType Directory -Force -Path $destination | Out-Null
    Get-ChildItem -LiteralPath $source -Recurse -File |
        Where-Object { $_.Extension -in $rule.Extensions } |
        ForEach-Object {
            $relative = $_.FullName.Substring($source.Length + 1)
            $target = Join-Path $destination $relative
            New-Item -ItemType Directory -Force -Path (Split-Path $target -Parent) | Out-Null
            Copy-Item -LiteralPath $_.FullName -Destination $target
        }
}

$manuscriptDestination = Join-Path $stage "manuscript"
New-Item -ItemType Directory -Path $manuscriptDestination | Out-Null
Get-ChildItem (Join-Path $root "manuscript") -File |
    Where-Object {
        $_.Extension -in ".md", ".json", ".txt", ".csv" -and
        $_.Length -lt 2MB -and
        $_.Name -notmatch "_final_paper\.md$"
    } |
    ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination $manuscriptDestination
    }

$taskDestination = Join-Path $stage "_tasks"
New-Item -ItemType Directory -Path $taskDestination | Out-Null
Copy-Item -Path (Join-Path $review "TASK_*.md") -Destination $taskDestination

$files = @(Get-ChildItem -LiteralPath $stage -Recurse -File | Sort-Object FullName)
$entries = foreach ($file in $files) {
    [ordered]@{
        path = $file.FullName.Substring($stage.Length + 1).Replace("\", "/")
        bytes = $file.Length
        sha256 = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    }
}

$manifest = [ordered]@{
    created_utc = (Get-Date).ToUniversalTime().ToString("o")
    source_root = $root
    source_control = [ordered]@{
        type = "none"
        commit = "NOT_A_GIT_REPOSITORY"
        branch = "NOT_A_GIT_REPOSITORY"
    }
    package_scope = "scripts, non-secret configs, derived machine-readable tables, current figures, manuscript/report sources, audit docs, rendered PDFs"
    excluded = "data/raw, raster and NetCDF upstream products, local DTM rasters, .git, caches, standalone Base64 HTML/Markdown, browser state, credentials"
    file_count = $entries.Count
    total_bytes = ($files | Measure-Object -Property Length -Sum).Sum
    files = $entries
}
$manifest | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $stage "PACKAGE_BASELINE_MANIFEST.json") -Encoding utf8

Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory(
    $stage,
    $zip,
    [System.IO.Compression.CompressionLevel]::Optimal,
    $false
)
$handoff = [ordered]@{
    source_control = "NOT_A_GIT_REPOSITORY"
    zip_path = $zip
    zip_bytes = (Get-Item $zip).Length
    zip_sha256 = (Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash.ToLowerInvariant()
    staged_files = @(Get-ChildItem $stage -Recurse -File).Count
}
$handoff | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $review "PACKAGE_HANDOFF.json") -Encoding utf8
$handoff | ConvertTo-Json
