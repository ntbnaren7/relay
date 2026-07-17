#!/usr/bin/env bash
set -e

REPO="ntbnaren7/relay"
INSTALL_DIR="/usr/local/bin"

if [ ! -w "$INSTALL_DIR" ]; then
  INSTALL_DIR="$HOME/.local/bin"
  mkdir -p "$INSTALL_DIR"
fi

OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
ARCH="$(uname -m)"

if [ "$OS" = "darwin" ]; then
  OS="macos"
fi

if [ "$ARCH" = "x86_64" ] || [ "$ARCH" = "amd64" ]; then
  ARCH="x64"
elif [ "$ARCH" = "arm64" ] || [ "$ARCH" = "aarch64" ]; then
  ARCH="arm64"
else
  echo "❌ Unsupported architecture: $ARCH"
  exit 1
fi

ASSET_NAME="relay-${OS}-${ARCH}"
echo "⬇️ Downloading Relay for ${OS}-${ARCH}..."

LATEST_URL="https://github.com/${REPO}/releases/latest/download/${ASSET_NAME}"
TEMP_FILE="$(mktemp)"

curl -fsSL -o "$TEMP_FILE" "$LATEST_URL"
chmod +x "$TEMP_FILE"
mv "$TEMP_FILE" "$INSTALL_DIR/relay"

# Remove macOS quarantine flag so Gatekeeper does not block execution
if [ "$OS" = "macos" ]; then
  xattr -d com.apple.quarantine "$INSTALL_DIR/relay" 2>/dev/null || true
fi

echo "🎉 Relay installed successfully to $INSTALL_DIR/relay"

if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
  echo "⚠️  Please add $INSTALL_DIR to your PATH to run 'relay' directly."
  echo "Run: export PATH=\"\$PATH:$INSTALL_DIR\" and add it to your ~/.zshrc or ~/.bashrc"
else
  echo "🚀 Run 'relay' to get started!"
fi
