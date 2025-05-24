#!/bin/bash

set -e  # abort on error

SERVICE_NAME="display.service"
SERVICE_NAME_WEB="web.service"
SERVICE_NAME_RFID="rfid.service"
SCRIPT_NAME="app.py"
ENV_FILE=".env"
SERVICE_PATH="/etc/systemd/system/"
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

# Install system dependencies
echo "📦 Installing required system packages..."
sudo apt-get update
sudo apt-get upgrade
					
sudo apt install -y python3 python3-pip libjpeg-dev libopenjp2-7 libopenblas0 \
  python3-flask python3-requests python3-numpy python3-pillow python3-dotenv python3-spidev \
 
sudo apt autoremove

# Spotipy (nur über pip verfügbar)
python3 -m pip install --upgrade pip
pip3 install --no-cache-dir spotipy python-dotenv --break-system-packages

# create certs
cd ~/iot_musiccontrol/
mkdir certs && cd certs/
openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout rpi.key -out rpi.crt

# Install and start systemd service
cd ~/iot_musiccontrol/
echo "🛠️ Installing systemd service for the display..."
sudo cp "$SERVICE_NAME" "$SERVICE_PATH"

# Install and start systemd service
echo "🛠️ Installing systemd service for web..."
sudo cp "$SERVICE_NAME_WEB" "$SERVICE_PATH"

# Install and start systemd service
echo "🛠️ Installing systemd service for rfid..."
sudo cp "$SERVICE_NAME_RFID" "$SERVICE_PATH"

# reloading service deamon
sudo systemctl daemon-reload

# enabling all services
echo "🔁 Enabling and starting service for the display..."
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"

echo "🔁 Enabling and starting service for web..."
sudo systemctl enable "$SERVICE_NAME_WEB"
sudo systemctl restart "$SERVICE_NAME_WEB"

echo "🔁 Enabling and starting service for rfid..."
sudo systemctl enable "$SERVICE_NAME_RFID"
sudo systemctl restart "$SERVICE_NAME_RFID"

echo "✅ Setup complete."

# Configure journald log rotation
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

# Reboot
read -p "🔁 Reboot now to activate? [y/N]: " REBOOT
if [[ "$REBOOT" =~ ^[Yy]$ ]]; then
  echo "🔄 Rebooting now..."
  sudo reboot
else
  echo "ℹ️ Please reboot manually before using the display."
fi