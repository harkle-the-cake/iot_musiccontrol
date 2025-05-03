#!/bin/bash

set -e  # abort on error

SERVICE_NAME="cover-display.service"
SCRIPT_NAME="app.py"
ENV_FILE=".env"
SERVICE_PATH="/etc/systemd/system/$SERVICE_NAME"
APP_DIR="$(pwd)"
CONFIG_FILE="/boot/config.txt"

echo "🔧 Starting full setup of cover-display in: $APP_DIR"

# 1. Install system dependencies
echo "📦 Installing required system packages..."
sudo apt update
sudo apt install -y python3 python3-pip python3-pil python3-dev python3-setuptools \
                    python3-spidev libjpeg-dev libopenblas-base git

# 2. Prompt for Spotify credentials
if [ ! -f "$ENV_FILE" ]; then
  echo "🔐 Enter your Spotify Developer credentials:"
  read -p "Client ID: " CLIENT_ID
  read -p "Client Secret: " CLIENT_SECRET

  echo "📄 Writing .env file..."
  cat > "$ENV_FILE" <<EOF
SPOTIFY_CLIENT_ID=$CLIENT_ID
SPOTIFY_CLIENT_SECRET=$CLIENT_SECRET
EOF
else
  echo "✅ Found existing .env – skipping credential input."
fi

# 3. Install Python packages
echo "🐍 Installing Python dependencies..."
pip3 install -r requirements.txt

# 4. Enable SPI if not already
if ! grep -q "^dtparam=spi=on" "$CONFIG_FILE"; then
  echo "🔌 Enabling SPI interface in $CONFIG_FILE..."
  echo "dtparam=spi=on" | sudo tee -a "$CONFIG_FILE" > /dev/null
  SPI_ENABLED_NOW=true
else
  echo "✅ SPI already enabled."
fi

# 5. Run app once for Spotify login
echo "🔑 Launching app for initial Spotify login..."
python3 "$SCRIPT_NAME"

# 6. Install and start systemd service
if [ ! -f "$SERVICE_PATH" ]; then
  echo "🛠️ Installing systemd service..."
  sudo cp "$SERVICE_NAME" "$SERVICE_PATH"
fi

echo "🔁 Enabling and starting service..."
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"

echo "✅ Setup complete."

# 7. Reboot if SPI was newly enabled
if [ "$SPI_ENABLED_NOW" = true ]; then
  read -p "🔁 SPI was just enabled. Reboot now to activate it? [y/N]: " REBOOT
  if [[ "$REBOOT" =~ ^[Yy]$ ]]; then
    echo "🔄 Rebooting now..."
    sudo reboot
  else
    echo "ℹ️ Please reboot manually before using the display."
  fi
fi
