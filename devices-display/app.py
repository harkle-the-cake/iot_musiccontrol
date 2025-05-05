#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
import argparse
import os
import sys
import time
import logging
import requests
import io
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from PIL import Image
import spidev as SPI
from pathlib import Path
from dotenv import load_dotenv

# Argument parsing
parser = argparse.ArgumentParser(description="Spotify Cover Display")
parser.add_argument("--once", "-o", action="store_true", help="Run once for authentication and exit")
args = parser.parse_args()

# Load environment variables from .env file
load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

cache_path = Path(__file__).resolve().parent / ".spotify_cache"

# Import display library (adjust if needed)
from libs import LCD_1inch3

# Read Spotify credentials from environment
client_id = os.getenv("SPOTIFY_CLIENT_ID")
client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")

if not client_id or not client_secret:
    raise ValueError("❌ Missing SPOTIFY_CLIENT_ID or SPOTIFY_CLIENT_SECRET in environment!")

if not (Path(__file__).resolve().parent / "images/default.jpg").exists():
    raise FileNotFoundError("⚠️ Default image not found: images/default.jpg")


# GPIO pin configuration
RST = 27
DC = 25
BL = 18
bus = 0
device = 0

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

# Initialize display
disp = LCD_1inch3.LCD_1inch3(
    spi=SPI.SpiDev(bus, device),
    spi_freq=10000000,
    rst=RST,
    dc=DC,
    bl=BL
)
disp.Init()
disp.clear()

# Initialize Spotify API authentication
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=client_id,
    client_secret=client_secret,
    redirect_uri="http://127.0.0.1:8888/callback",
    scope="user-read-playback-state user-read-private user-read-email",
    cache_path = Path(__file__).resolve().parent / ".spotify_cache",
    open_browser=False
))

last_track_id = None

def mapToImage(device):
    """Return local image path for a given Spotify device dict."""
    device_id = device.get('id')
    device_name = device.get('name', 'unknown').lower().replace(" ", "_")
    
    # Load mapping file (can be JSON or just file lookup)
    images_dir = Path(__file__).resolve().parent / "images"
    specific_path = images_dir / f"{device_id}.jpg"
    fallback_path = images_dir / f"{device_name}.jpg"
    default_path = images_dir / "default.jpg"

    if specific_path.exists():
        logging.info(f"🔗 Found image for device ID: {device_id}")
        return specific_path
    elif fallback_path.exists():
        logging.info(f"🔗 Found image for device name: {device_name}")
        return fallback_path
    else:
        logging.warning("🖼 No image found, using default.")
        return default_path

def show_device(image_path):
    """Load and show image from given path."""
    try:
        image = Image.open(image_path).convert("RGB")
        image = image.resize((disp.width, disp.height))
        disp.ShowImage(image)
    except Exception as e:
        logging.error(f"Failed to load or display device image: {e}")

def process_once():
    """Fetch current track and show cover once."""
    try:
        playback = sp.current_playback()
        if playback and playback.get('device'):
            device = playback['device']
            logging.info(f"🎵 Now playing on device: {device.get('name', 'Unknown')} ({device.get('id', 'no-id')})")
            image_url = mapToImage(device)
            show_device(image_url)
        else:
            logging.warning("⏸ No track playing or playback data available.")
    except Exception as e:
        logging.error(f"Error while querying Spotify playback: {e}")

if args.once:
    logging.info("▶️ Run-once mode activated (for initial Spotify login).")
    process_once()
    sys.exit(0)

# Normal loop mode
while True:
    process_once()
    time.sleep(5)
