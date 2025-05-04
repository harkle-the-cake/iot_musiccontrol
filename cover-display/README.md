# Cover Display on Raspberry Pi

Display the album cover of the currently playing Spotify track using a 1.3" SPI TFT display on a Raspberry Pi Zero.  
Built for minimal systems with beautiful output and easy integration.

![example](docs/preview.jpg) <!-- Optional Screenshot -->

---

## ✨ Features

- 🔁 Polls Spotify every few seconds for current playback
- 🖼 Downloads and displays the album cover of the current track
- 🧲 Designed to be embedded into custom enclosures (e.g. wood box, magnet mount)
- 💡 Runs automatically as a systemd service

---

## 🧰 Requirements

- Raspberry Pi Zero (or any Pi with SPI)
- 1.3" TFT SPI Display (ST7789, via `LCD_1inch3.py`)
- Python 3.x
- Spotify Premium account (required for playback access)

---

## 📦 Installation

```🛠 automatic installation (Raspberry Pi Setup)
This project is designed to run on a clean Raspberry Pi OS installation.

To install all dependencies, configure the display, and set up the systemd service, simply run:
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get git
git clone https://github.com/harkle-the-cake/iot_musiccontrol.git
cd cover-display
chmod +x setup.sh
./setup.sh

This will:

🧱 Install required system packages (Python, SPI, libraries)

🔐 Prompt you for your Spotify Client ID and Client Secret

📄 Create a .env file to store credentials

🖼 Run the app once to complete the Spotify login (interactive browser-based)

🛠 Install and start the cover-display systemd service

🔌 Enable the SPI interface (if not already)

🔁 Offer to reboot the Pi (required if SPI was just enabled)

After reboot, the display will automatically show the album cover of the currently playing Spotify track.


``` manual installation
use the bash and clone this repository:

sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get git
git clone https://github.com/harkle-the-cake/iot_musiccontrol.git
cd cover-display

Install dependencies
pip3 install -r requirements.txt


```Env file
Create a .env file based on the example:
cp .env.example .env
Edit .env and insert your Spotify client ID and secret:
SPOTIFY_CLIENT_ID=your-client-id
SPOTIFY_CLIENT_SECRET=your-client-secret


---

``` 🚀 Run manually
Run manually

/usr/bin/python3 /home/pi/cover-display/app.py

---
## 🔁 Run as a service (recommended)
Copy the "cover-display.service" to the systemd folder.

sudo systemctl daemon-reload
sudo systemctl enable cover-display.service
sudo systemctl start cover-display.service

📄 License
MIT License.
Credits to Waveshare for the original display driver base.

🤝 Contributing
Pull requests welcome. Feel free to submit issues, suggestions, or enhancements.