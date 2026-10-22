#Requires -Version 5.1
<#
.SYNOPSIS
    Cross-platform Windows setup script for whisper.api and whisper.cpp (whisper-cli).
.DESCRIPTION
    Clones innovatorved/whisper.cpp (develop branch), compiles whisper-cli using CMake
    (supporting Visual Studio MSVC, Ninja, or MinGW), installs binary/whisper-cli.exe,
    and ensures the default tiny.en model is present.
#>

$ErrorActionPreference = "Stop"

function Write-SetupLog([string]$Message) {
    Write-Host "[SETUP] $Message" -ForegroundColor Green
}

function Write-SetupWarn([string]$Message) {
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Write-SetupError([string]$Message) {
    Write-Host "[ERROR] $Message" -ForegroundColor Red
    exit 1
}

# --- 1. Dependency Checks ---
Write-SetupLog "Checking required build tools (git, cmake)..."
foreach ($cmd in @("git", "cmake")) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        Write-SetupError "'$cmd' is not installed or not in PATH. Please install it (e.g., via winget or choco) and try again."
    }
}

if (-not (Get-Command "ffmpeg" -ErrorAction SilentlyContinue)) {
    Write-SetupWarn "'ffmpeg' was not found in PATH. Audio/video format conversion requires ffmpeg at runtime (install via: winget install Gyan.FFmpeg)."
}

# --- 2. Clone Repository ---
$RepoUrl = if ($env:WHISPER_REPO_URL) { $env:WHISPER_REPO_URL } else { "https://github.com/innovatorved/whisper.cpp.git" }
$Branch = if ($env:WHISPER_BRANCH) { $env:WHISPER_BRANCH } else { "develop" }
$BuildDir = Join-Path $PSScriptRoot "whisper_temp_build"

if (Test-Path $BuildDir) {
    Write-SetupWarn "Directory '$BuildDir' already exists. Removing it for a clean build..."
    Remove-Item -Recurse -Force $BuildDir
}

Write-SetupLog "Cloning $RepoUrl (branch: $Branch)..."
git clone --depth 1 --branch $Branch $RepoUrl $BuildDir
if ($LASTEXITCODE -ne 0) {
    Write-SetupWarn "Cloning branch '$Branch' failed; falling back to default branch..."
    git clone --depth 1 $RepoUrl $BuildDir
    if ($LASTEXITCODE -ne 0) {
        Write-SetupError "Failed to clone $RepoUrl"
    }
}

Push-Location $BuildDir
try {
    # --- 3. Configure & Build with CMake ---
    $CmakeArgs = @(
        "-S", ".",
        "-B", "build",
        "-DBUILD_SHARED_LIBS=OFF",
        "-DWHISPER_BUILD_TESTS=OFF",
        "-DWHISPER_BUILD_EXAMPLES=ON",
        "-DGGML_NATIVE=OFF"
    )

    if (Get-Command "nvcc" -ErrorAction SilentlyContinue) {
        Write-SetupLog "NVIDIA CUDA compiler (nvcc) detected. Enabling CUDA support."
        $CmakeArgs += "-DGGML_CUDA=ON"
    }

    Write-SetupLog "Configuring CMake..."
    & cmake @CmakeArgs
    if ($LASTEXITCODE -ne 0) {
        Write-SetupError "CMake configuration failed."
    }

    Write-SetupLog "Building whisper-cli (Release configuration)..."
    & cmake --build build --config Release --target whisper-cli --parallel
    if ($LASTEXITCODE -ne 0) {
        Write-SetupWarn "Targeted build failed; attempting full Release build..."
        & cmake --build build --config Release --parallel
        if ($LASTEXITCODE -ne 0) {
            Write-SetupError "CMake build failed."
        }
    }

    # --- 4. Locate Compiled Binary ---
    $Candidates = @(
        "build\bin\Release\whisper-cli.exe",
        "build\bin\whisper-cli.exe",
        "build\Release\whisper-cli.exe",
        "bin\Release\whisper-cli.exe",
        "bin\whisper-cli.exe",
        "build\bin\whisper-cli"
    )

    $FoundBinary = $null
    foreach ($Candidate in $Candidates) {
        if (Test-Path $Candidate) {
            $FoundBinary = (Resolve-Path $Candidate).Path
            break
        }
    }

    if (-not $FoundBinary) {
        $Search = Get-ChildItem -Path "build" -Filter "whisper-cli*" -Recurse -File -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($Search) {
            $FoundBinary = $Search.FullName
        }
    }

    if (-not $FoundBinary) {
        Write-SetupError "Could not locate compiled whisper-cli.exe in build output."
    }

    Write-SetupLog "Found compiled binary: $FoundBinary"

    # --- 5. Install Binary ---
    $DestDir = Join-Path $PSScriptRoot "binary"
    if (-not (Test-Path $DestDir)) {
        New-Item -ItemType Directory -Path $DestDir | Out-Null
    }

    $DestExe = Join-Path $DestDir "whisper-cli.exe"
    Copy-Item -Path $FoundBinary -Destination $DestExe -Force
    Write-SetupLog "Installed binary to $DestExe"
}
finally {
    Pop-Location
}

# --- 6. Clean Up Build Directory ---
Write-SetupLog "Cleaning up temporary build directory..."
Remove-Item -Recurse -Force $BuildDir -ErrorAction SilentlyContinue

# --- 7. Download Default Model (If Needed) ---
$ModelsDir = Join-Path $PSScriptRoot "models"
if (-not (Test-Path $ModelsDir)) {
    New-Item -ItemType Directory -Path $ModelsDir | Out-Null
}

$ModelName = if ($env:DEFAULT_MODEL) { $env:DEFAULT_MODEL } else { "tiny.en" }
$ModelPath = Join-Path $ModelsDir "ggml-$ModelName.bin"
$ModelUrl = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-$ModelName.bin"

if (-not (Test-Path $ModelPath)) {
    Write-SetupLog "Downloading default model ($ModelName) to $ModelPath..."
    try {
        Invoke-WebRequest -Uri $ModelUrl -OutFile $ModelPath -UseBasicParsing
        Write-SetupLog "Downloaded $ModelPath successfully."
    }
    catch {
        Write-SetupWarn "Could not download $ModelName model now: $_. Python will download required models on startup."
    }
}
else {
    Write-SetupLog "Default model already exists at $ModelPath."
}

# --- 8. Verification ---
$InstalledExe = Join-Path $PSScriptRoot "binary\whisper-cli.exe"
if (Test-Path $InstalledExe) {
    Write-SetupLog "Verification: Binary exists at $InstalledExe"
}
else {
    Write-SetupError "Binary installation verification failed at $InstalledExe"
}

Write-SetupLog "Windows setup completed successfully!"
