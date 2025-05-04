#!/bin/bash

set -e  # abort on error

SERVICE_NAME="devices-display.service"
SERVICE_NAME_UPLOAD="image-upload.service"
SCRIPT_NAME="app.py"
ENV_FILE=".env"
SERVICE_PATH="/etc/systemd/system/$SERVICE_NAME"
SERVICE_PATH_UPLOAD="/etc/systemd/system/$SERVICE_NAME_UPLOAD"
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
python3 "$SCRIPT_NAME" --once

# 6. Install and start systemd service
if [ ! -f "$SERVICE_PATH" ]; then
  echo "🛠️ Installing systemd service..."
  sudo cp "$SERVICE_NAME" "$SERVICE_PATH"
fi

echo "🔁 Enabling and starting service..."
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"

# 6.1 Install and start systemd service
if [ ! -f "$SERVICE_PATH_UPLOAD" ]; then
  echo "🛠️ Installing systemd service for image upload..."
  sudo cp "$SERVICE_NAME_UPLOAD" "$SERVICE_PATH_UPLOAD"
fi

echo "🔁 Enabling and starting service for image upload..."
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME_UPLOAD"
sudo systemctl restart "$SERVICE_NAME_UPLOAD"

echo "✅ Setup complete."

# 7. Configure journald log rotation
echo "🗂 Configuring journald log rotation..."

JOURNAL_CONF="/etc/systemd/journald.conf"
NEEDS_RESTART=false

sudo grep -q "^SystemMaxUse=" $JOURNAL_CONF || {
    echo "SystemMaxUse=50M" | sudo tee -a $JOURNAL_CONF
    NEEDS_RESTART=true
}

sudo grep -q "^SystemMaxFileSize=" $JOURNAL_CONF || {
    echo "SystemMaxFileSize=10M" | sudo tee -a $JOURNAL_CONF
    NEEDS_RESTART=true
}

sudo grep -q "^MaxRetentionSec=" $JOURNAL_CONF || {
    echo "MaxRetentionSec=7day" | sudo tee -a $JOURNAL_CONF
    NEEDS_RESTART=true
}

if [ "$NEEDS_RESTART" = true ]; then
    echo "🔄 Restarting journald to apply log rotation settings..."
    sudo systemctl restart systemd-journald
else
    echo "✅ Journald already configured."
fi

# 8. Reboot
read -p "🔁 Reboot now to activate? [y/N]: " REBOOT
if [[ "$REBOOT" =~ ^[Yy]$ ]]; then
  echo "🔄 Rebooting now..."
  sudo reboot
else
  echo "ℹ️ Please reboot manually before using the display."
fi