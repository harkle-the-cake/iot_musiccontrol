#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
import argparse
import os
import sys
import time
import logging
import requests
import io
import json
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from PIL import Image
import spidev as SPI
from pathlib import Path
from dotenv import load_dotenv
# Import display library (adjust if needed)
from libs import LCD_1inch3

# vars
code_patch = ""
last_track_id = None

# GPIO pin configuration
RST = 27
DC = 25
BL = 18
bus = 0
device = 0

cache_path = Path(__file__).resolve().parent / ".spotify_cache"

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


def mapToImage(device):
    """Return local image path for a given Spotify device dict."""
    device_id = device.get('id')
    device_name = device.get('name', 'unknown').lower().replace(" ", "_")
    
    # Load mapping file (can be JSON or just file lookup)
    images_dir = Path(__file__).resolve().parent / "static" / "images"
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

# Konfiguration laden
def load_config():
    config_path = Path(__file__).resolve().parent / "config.json"
    if config_path.exists():
        with open(config_path) as f:
            import json
            return json.load(f)
    return {"mode": "device"}

def show_image_from_url(url):
    try:
        import requests, io
        from PIL import Image
        response = requests.get(url)
        image = Image.open(io.BytesIO(response.content)).convert("RGB")
        image = image.resize((disp.width, disp.height))
        disp.ShowImage(image)
    except Exception as e:
        logging.error(f"Failed to load image from URL: {e}")

def process_once():
    config = load_config()
    mode = config.get("mode", "device")

    try:
        playback = sp.current_playback()
        if not playback:
            logging.warning("⏸ No playback available.")
            return

        if mode == "device":
            device = playback.get("device")
            if device:
                image_path = mapToImage(device)
                show_device(image_path)
            else:
                logging.warning("🔌 No device info.")
        elif mode in ["album", "playlist", "artist"]:
            context = playback.get("context", {})
            logging.debug(f"🔍 Playback-Kontext: {json.dumps(context, indent=2)}")
            
            if context and context.get("type") == mode:
                if context["type"] == "artist" and not context["uri"].startswith("spotify:artist"):
                    logging.warning("⚠️ No artist URI in context.")
                    return
                uri = context["uri"]
                if mode == "artist":
                    artist_id = uri.split(":")[-1]
                    artist = sp.artist(artist_id)
                    images = artist.get("images", [])
                elif mode == "playlist":
                    playlist_id = uri.split(":")[-1]
                    playlist = sp.playlist(playlist_id)
                    images = playlist.get("images", [])
                elif mode == "album":
                    album_id = uri.split(":")[-1]
                    album = sp.album(album_id)
                    images = album.get("images", [])
                else:
                    images = []

                if images:
                    show_image_from_url(images[0]["url"])
                else:
                    logging.warning("🖼 No images found in context.")
            else:
                logging.warning(f"🎯 No {mode} context.")
        elif mode == "delete":
            delete_image = Path(__file__).resolve().parent / "static/images/delete.jpg"
            if delete_image.exists():
                show_device(delete_image)
            else:
                logging.warning("🗑 Kein delete.jpg gefunden.")
        else:
            logging.warning(f"❓ Unbekannter Modus: {mode}")

    except Exception as e:
        logging.error(f"Error in process_once(): {e}")

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

config = load_config()
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=config.get("client_id"),
    client_secret=config.get("client_secret"),
    redirect_uri=config.get("redirect_uri"),
    scope="user-read-playback-state user-modify-playback-state user-read-private user-read-email",
    cache_path=Path(__file__).resolve().parent / ".spotify_cache",
    open_browser=False
))

# Normal loop mode
while True:
    process_once()
    time.sleep(5)
