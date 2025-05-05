#!/bin/bash

set -e  # abort on error

SERVICE_NAME="cover-display.service"
SCRIPT_NAME="app.py"
ENV_FILE=".env"
SERVICE_PATH="/etc/systemd/system/$SERVICE_NAME"
APP_DIR="$(pwd)"
CONFIG_FILE="/boot/config.txt"

echo "🔧 Starting full setup of cover-display in: $APP_DIR"

# 0. Ensure SPI is enabled (before any display logic)
CONFIG_FILE="/boot/config.txt"
if ! grep -q "^dtparam=spi=on" "$CONFIG_FILE"; then
  echo "🔧 SPI interface not enabled – enabling now..."
  echo "dtparam=spi=on" | sudo tee -a "$CONFIG_FILE" > /dev/null
  echo "⚠️ SPI was just enabled – a reboot is required before continuing."
  read -p "🔁 Reboot now? [Y/n]: " REBOOT
  if [[ "$REBOOT" =~ ^[Nn]$ ]]; then
    echo "ℹ️ Please reboot manually and re-run the setup after reboot."
    exit 0
  else
    sudo reboot
  fi
else
  echo "✅ SPI already enabled."
fi

# 1. Install system dependencies
echo "📦 Installing required system packages..."
sudo apt update

sudo apt install -y python3 python3-pip libjpeg-dev libopenjp2-7 libopenblas0 \
  python3-flask python3-requests python3-numpy python3-pillow python3-dotenv python3-spidev \
 
sudo apt autoremove

# Spotipy (nur über pip verfügbar)
pip3 install --no-cache-dir spotipy python-dotenv --break-system-packages

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

# 4. Run app once for Spotify login
echo "🔑 Launching app for initial Spotify login..."
python3 "$SCRIPT_NAME" --once

# 5. Install and start systemd service
if [ ! -f "$SERVICE_PATH" ]; then
  echo "🛠️ Installing systemd service..."
  sudo cp "$SERVICE_NAME" "$SERVICE_PATH"
fi

echo "🔁 Enabling and starting service..."
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"

echo "✅ Setup complete."

# 6. Configure journald log rotation
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

# 7. Reboot
read -p "🔁 Reboot now to activate? [y/N]: " REBOOT
if [[ "$REBOOT" =~ ^[Yy]$ ]]; then
  echo "🔄 Rebooting now..."
  sudo reboot
else
  echo "ℹ️ Please reboot manually before using the display."
fi