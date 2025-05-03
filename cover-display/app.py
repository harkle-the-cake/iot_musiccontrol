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

# Import display library (adjust if needed)
from libs import LCD_1inch3

# Read Spotify credentials from environment
client_id = os.getenv("SPOTIFY_CLIENT_ID")
client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")

if not client_id or not client_secret:
    raise ValueError("❌ Missing SPOTIFY_CLIENT_ID or SPOTIFY_CLIENT_SECRET in environment!")

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
    scope="user-read-playback-state",
    open_browser=False
))

last_track_id = None

def show_cover(url):
    """Downloads and displays the album cover image from a given URL."""
    logging.debug(f"Fetching cover image: {url}")
    try:
        response = requests.get(url)
        image = Image.open(io.BytesIO(response.content)).convert("RGB")
        image = image.resize((disp.width, disp.height))
        disp.ShowImage(image)
    except Exception as e:
        logging.error(f"Failed to load or display cover image: {e}")

def process_once():
    """Fetch current track and show cover once."""
    try:
        playback = sp.current_playback()
        if playback and playback.get('item'):
            track = playback['item']
            logging.info(f"🎵 Now playing: {track['name']} – {track['artists'][0]['name']}")
            image_url = track['album']['images'][0]['url']
            show_cover(image_url)
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
