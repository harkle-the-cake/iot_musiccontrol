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
    level=logging.INFO,
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

# Konfiguration laden
def load_config():
    config_path = Path(__file__).resolve().parent / "config.json"
    if config_path.exists():
        with open(config_path) as f:
            import json
            return json.load(f)
    return {"mode": "device"}


def show_device(image_path):
    try:
        from PIL import Image
        image = Image.open(image_path).convert("RGB")
        config = load_config()
        rotation = int(config.get("rotation", 0))
        if rotation != 0:
            image = image.rotate(rotation, expand=True)
        image = image.resize((disp.width, disp.height))
        disp.ShowImage(image)
    except Exception as e:
        logging.error(f"Failed to load or display device image: {e}")

def show_image_from_url(url):
    try:
        import requests, io
        from PIL import Image
        response = requests.get(url)
        image = Image.open(io.BytesIO(response.content)).convert("RGB")
        config = load_config()
        rotation = int(config.get("rotation", 0))
        if rotation != 0:
            image = image.rotate(rotation, expand=True)
        image = image.resize((disp.width, disp.height))
        disp.ShowImage(image)
    except Exception as e:
        logging.error(f"Failed to load image from URL: {e}")

def show_local_fallback(image_name):
    fallback_path = Path(__file__).resolve().parent / "static/images" / image_name
    if fallback_path.exists():
        show_device(fallback_path)
        logging.info(f"🖼 Fallback-Bild angezeigt: {image_name}")
    else:
        logging.warning(f"❌ Kein Fallback-Bild gefunden: {image_name}")

def process_once():
    config = load_config()
    mode = config.get("displayMode", "device")
    initialMode = mode
    try:
        playback = sp.current_playback()
        if not playback:
            logging.warning("⏸ No playback available.")
            show_local_fallback("no_image.jpg")
            return

        context = playback.get("context", {})
        context_type = context.get("type", "")
        uri = context.get("uri", "")

        if mode == "delete":
            show_local_fallback("delete.jpg")
            return

        if mode == "auto":
            if context_type:
                mode = context_type

        if mode == "device":
            device = playback.get("device")
            if device:
                image_path = mapToImage(device)
                show_device(image_path)
            else:
                show_local_fallback("default_device.jpg")

        elif mode == "album":
            item = playback.get("item")
            images = item.get("album", {}).get("images", []) if item else []
            if images:
                show_image_from_url(images[0]["url"])
            else:
                show_local_fallback("default_album.jpg")

        elif mode == "playlist":
            try:
                playlist_id = uri.split(":")[-1]
                playlist = sp.playlist(playlist_id)
                images = playlist.get("images", [])
                if images:
                    show_image_from_url(images[0]["url"])
                else:
                    show_local_fallback("default_playlist.jpg")
                    raise Exception("No images in playlist")
            except Exception as e:
                logging.warning(f"⚠️ Fehler beim Playlist-Aufruf: {e}")
                if initialMode == "auto":    
                    item = playback.get("item")                    
                    track_images = item.get("album", {}).get("images", []) if item else []
                    if track_images:
                        show_image_from_url(track_images[0]["url"])
                    else:
                        show_local_fallback("default_playlist.jpg")
                else:
                    show_local_fallback("default_playlist.jpg")

        elif mode == "artist":
            try:
                artist_id = uri.split(":")[-1]
                artist = sp.artist(artist_id)
                images = artist.get("images", [])
                if images:
                    show_image_from_url(images[0]["url"])
                else:
                    show_local_fallback("default_artist.jpg")
                    raise Exception("No artist image")
            except Exception as e:
                logging.warning(f"⚠️ Fehler beim Artist-Aufruf: {e}")
                if initialMode == "auto":                    
                    item = playback.get("item")
                    track_images = item.get("album", {}).get("images", []) if item else []
                    if track_images:
                        show_image_from_url(track_images[0]["url"])
                    else:
                        show_local_fallback("default_artist.jpg")
                else:
                    show_local_fallback("default_artist.jpg")

        else:
            logging.warning(f"❓ Unbekannter Modus: {mode}")
            show_local_fallback("mode_unknown.jpg")

    except Exception as e:
        logging.error(f"❌ Fehler in process_once(): {e}")
        show_local_fallback("error.jpg")

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
