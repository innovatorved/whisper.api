#!/usr/bin/env bash
set -e          # Exit immediately if a command exits with a non-zero status.
set -o pipefail # Return value of a pipeline is the status of the last command to exit with a non-zero status.

# --- Helper Functions ---
log() {
    echo -e "\033[1;32m[SETUP] $1\033[0m"
}

warn() {
    echo -e "\033[1;33m[WARN] $1\033[0m"
}

error() {
    echo -e "\033[1;31m[ERROR] $1\033[0m"
    exit 1
}

# --- 1. Dependency Checks ---
log "Checking dependencies..."
for cmd in git cmake; do
    if ! command -v "$cmd" &> /dev/null; then
        error "$cmd is not installed. Please install it and try again."
    fi
done

# Check for a C++ compiler
if ! command -v g++ &> /dev/null && ! command -v clang++ &> /dev/null && ! command -v c++ &> /dev/null; then
    error "No C++ compiler found (g++, clang++, or c++). Please install a C++ toolchain."
fi

if ! command -v ffmpeg &> /dev/null; then
    warn "ffmpeg is not installed or not in PATH. Audio/video format conversion requires ffmpeg at runtime."
fi

# --- 2. Clone Repository ---
REPO_URL="${WHISPER_REPO_URL:-https://github.com/innovatorved/whisper.cpp.git}"
DIR_NAME="whisper_temp_build"
BRANCH="${WHISPER_BRANCH:-develop}"

if [ -d "$DIR_NAME" ]; then
    warn "Directory '$DIR_NAME' already exists. Removing it to ensure a clean build..."
    rm -rf "$DIR_NAME"
fi

log "Cloning repository from $REPO_URL (branch: $BRANCH)..."
if ! git clone --depth 1 --branch "$BRANCH" "$REPO_URL" "$DIR_NAME" 2>/dev/null; then
    warn "Branch '$BRANCH' not found or shallow clone failed; cloning default branch..."
    git clone --depth 1 "$REPO_URL" "$DIR_NAME"
fi
cd "$DIR_NAME"

# --- 3. Platform & Architecture Detection ---
OS=$(uname -s)
ARCH=$(uname -m)

log "Detected Platform: $OS ($ARCH)"

CMAKE_FLAGS="-DBUILD_SHARED_LIBS=OFF -DWHISPER_BUILD_TESTS=OFF -DWHISPER_BUILD_EXAMPLES=ON"

case "$OS" in
    Darwin*)
        log "macOS detected. Enabling Apple Accelerate and Metal support."
        CMAKE_FLAGS="$CMAKE_FLAGS -DGGML_METAL=ON -DGGML_ACCELERATE=ON"
        if [ "${WHISPER_COREML:-0}" = "1" ]; then
            log "Enabling CoreML support (WHISPER_COREML=1)."
            CMAKE_FLAGS="$CMAKE_FLAGS -DWHISPER_COREML=ON"
        fi
        ;;
    Linux*)
        if [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
            log "Linux ARM64 architecture detected. Using portable ARM flags..."
            export CFLAGS="${CFLAGS:-} -fPIC"
            export CXXFLAGS="${CXXFLAGS:-} -fPIC"
            CMAKE_FLAGS="$CMAKE_FLAGS -DGGML_NATIVE=OFF"
        fi

        if command -v nvcc &> /dev/null && command -v nvidia-smi &> /dev/null; then
            log "NVIDIA CUDA toolkit and GPU detected. Enabling CUDA support."
            CMAKE_FLAGS="$CMAKE_FLAGS -DGGML_CUDA=ON"
        elif command -v nvidia-smi &> /dev/null; then
            warn "NVIDIA GPU detected via nvidia-smi, but 'nvcc' compiler was not found. Building with CPU backend."
        fi
        ;;
    MINGW*|MSYS*|CYGWIN*)
        log "Windows (MSYS2/MinGW/Git Bash) detected."
        CMAKE_FLAGS="$CMAKE_FLAGS -DGGML_NATIVE=OFF"
        ;;
    *)
        warn "Unrecognized OS '$OS'. Proceeding with generic CMake flags."
        ;;
esac

# --- 4. Build ---
log "Configuring CMake with flags: $CMAKE_FLAGS"
if ! cmake -S . -B build $CMAKE_FLAGS; then
    error "CMake configuration failed."
fi

log "Compiling whisper-cli..."
if ! cmake --build build --config Release --target whisper-cli -j; then
    warn "Target 'whisper-cli' build returned non-zero; attempting full Release build..."
    if ! cmake --build build --config Release -j; then
        error "Build failed."
    fi
fi

# Locate Binary (Unix and Windows paths)
BINARY_SOURCE=""
for candidate in \
    "build/bin/whisper-cli" \
    "build/bin/Release/whisper-cli.exe" \
    "build/bin/whisper-cli.exe" \
    "bin/whisper-cli" \
    "whisper-cli" \
    "main"; do
    if [ -f "$candidate" ]; then
        BINARY_SOURCE="$candidate"
        break
    fi
done

if [ -z "$BINARY_SOURCE" ]; then
    BINARY_SOURCE=$(find build -name "whisper-cli*" -type f 2>/dev/null | head -n 1 || true)
fi

if [ -z "$BINARY_SOURCE" ]; then
    error "Could not locate compiled whisper-cli binary."
fi

log "Found compiled binary: $BINARY_SOURCE"

# --- 5. Install Binary ---
cd .. # Return to project root

DEST_DIR="binary"
mkdir -p "$DEST_DIR"

if [[ "$BINARY_SOURCE" == *.exe ]]; then
    DEST_BINARY="$DEST_DIR/whisper-cli.exe"
else
    DEST_BINARY="$DEST_DIR/whisper-cli"
fi

log "Installing binary to $DEST_BINARY..."
cp "$DIR_NAME/$BINARY_SOURCE" "$DEST_BINARY"
chmod +x "$DEST_BINARY" 2>/dev/null || true

# Also create a extensionless copy on Windows Git Bash if needed
if [[ "$DEST_BINARY" == *.exe ]] && [ ! -f "$DEST_DIR/whisper-cli" ]; then
    cp "$DEST_BINARY" "$DEST_DIR/whisper-cli" || true
fi

# --- 6. Clean Up ---
log "Cleaning up temporary build directory..."
rm -rf "$DIR_NAME"

# --- 7. Update .gitignore ---
GITIGNORE=".gitignore"
touch "$GITIGNORE"

for entry in "binary/" "models/" "whisper_temp_build/"; do
    if ! grep -q "^${entry}" "$GITIGNORE"; then
        echo "$entry" >> "$GITIGNORE"
        log "Added '$entry' to $GITIGNORE"
    fi
done

# --- 8. Download Default Model (If Needed) ---
MODEL="${DEFAULT_MODEL:-tiny.en}"
MODEL_PATH="models/ggml-$MODEL.bin"
MODEL_URL="https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-$MODEL.bin"

mkdir -p models
if [ ! -f "$MODEL_PATH" ]; then
    if command -v curl &> /dev/null; then
        log "Downloading default model ($MODEL) to $MODEL_PATH..."
        curl -L --fail --progress-bar "$MODEL_URL" -o "$MODEL_PATH" || warn "Could not download $MODEL_PATH now; the app will download models on startup."
    elif command -v wget &> /dev/null; then
        log "Downloading default model ($MODEL) to $MODEL_PATH..."
        wget -q --show-progress "$MODEL_URL" -O "$MODEL_PATH" || warn "Could not download $MODEL_PATH now; the app will download models on startup."
    else
        warn "Neither curl nor wget found. Models will be downloaded automatically by Python on startup."
    fi
else
    log "Default model found at $MODEL_PATH."
fi

# --- 9. Verification ---
if [ -x "$DEST_BINARY" ] || [ -f "$DEST_BINARY" ]; then
    log "Verification: Binary exists at $DEST_BINARY."
    "$DEST_BINARY" --help 2>&1 | head -n 5 || true
else
    error "Binary not found or not executable at $DEST_BINARY"
fi

log "Setup completed successfully!"
