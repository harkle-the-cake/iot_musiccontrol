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
from spotipy.oauth2 import SpotifyClientCredentials
from PIL import Image
import spidev as SPI
from pathlib import Path
from dotenv import load_dotenv
# Import display library (adjust if needed)
from libs import LCD_1inch3
import requests
import threading
from spotipy.exceptions import SpotifyException

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

logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("requests").propagate = True
logging.getLogger("urllib3").setLevel(logging.WARNING)
# Disable all child loggers of urllib3, e.g. urllib3.connectionpool
logging.getLogger("urllib3").propagate = True

def get_current_status():
    try:
        r = requests.get("http://127.0.0.1:5055/status", timeout=1)
        return r.json().get("value", "playing")
    except:
        return "playing"

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
        logging.debug(f"🔗 Found image for device ID: {device_id}")
        return specific_path
    elif fallback_path.exists():
        logging.debug(f"🔗 Found image for device name: {device_name}")
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
    return {"mode": "device"}# Konfiguration laden
    
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

def show_image_from_url(url, cache_name=None):
    import requests, io
    from PIL import Image
    from pathlib import Path

    try:
        config = load_config()
        rotation = int(config.get("rotation", 0))

        # Cache-Verzeichnis
        cache_dir = Path(__file__).resolve().parent / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)

        # Cache-Dateiname
        if cache_name:
            cache_path = cache_dir / f"{cache_name}.jpg"
        else:
            # Fallback: nutze gehashte URL als Dateiname
            import hashlib
            hashname = hashlib.sha256(url.encode()).hexdigest()
            cache_path = cache_dir / f"{hashname}.jpg"

        # Lade aus Cache oder von URL
        if cache_path.exists():
            logging.debug(f"🖼 Lade Bild aus Cache: {cache_path}")
            image = Image.open(cache_path)
        else:
            logging.debug(f"🌐 Lade Bild von URL: {url}")
            response = requests.get(url, timeout=5)
            image = Image.open(io.BytesIO(response.content)).convert("RGB")
            image.save(cache_path)
            logging.debug(f"💾 Bild gespeichert unter: {cache_path}")

        # Rotation & Resize
        if rotation != 0:
            image = image.rotate(rotation, expand=True)
        image = image.resize((disp.width, disp.height))

        # Anzeige
        disp.ShowImage(image)

    except Exception as e:
        logging.error(f"❌ Fehler beim Anzeigen des Bildes von URL: {e}")

def cleanup_image_cache(days_old=3):
    """Löscht Bilddateien aus dem Cache, die älter als `days_old` Tage sind."""
    cache_dir = Path(__file__).resolve().parent / "cache"
    if not cache_dir.exists():
        logging.debug("🧹 Kein Cache-Verzeichnis vorhanden.")
        return

    now = time.time()
    cutoff = now - (days_old * 86400)  # 86400 Sekunden pro Tag

    deleted = 0
    for file in cache_dir.glob("*.jpg"):
        try:
            if file.stat().st_mtime < cutoff:
                file.unlink()
                logging.info(f"🗑️  Alte Cache-Datei gelöscht: {file.name}")
                deleted += 1
        except Exception as e:
            logging.warning(f"⚠️  Fehler beim Löschen von {file.name}: {e}")

    if deleted > 0:
        logging.info(f"✅ {deleted} Cache-Datei(en) entfernt.")
    else:
        logging.debug("🧼 Keine veralteten Cache-Dateien gefunden.")

def start_cleanup_thread(interval_hours=6, days_old=3):
    """Startet einen Hintergrund-Thread, der regelmäßig den Cache aufräumt."""

    def run():
        while True:
            logging.debug("🧵 Starte Cache-Aufräum-Thread...")
            cleanup_image_cache(days_old=days_old)
            logging.debug(f"🕒 Nächster Durchlauf in {interval_hours} Stunden.")
            time.sleep(interval_hours * 3600)

    t = threading.Thread(target=run, daemon=True)
    t.start()
    logging.info(f"🚀 Hintergrund-Thread zum Cache-Aufräumen gestartet (alle {interval_hours}h).")

def show_local_fallback(image_name):
    fallback_path = Path(__file__).resolve().parent / "static/images" / image_name
    if fallback_path.exists():
        show_device(fallback_path)
        logging.debug(f"🖼 Fallback-Bild angezeigt: {image_name}")
    else:
        logging.warning(f"❌ Kein Fallback-Bild gefunden: {image_name}")

def show_artist_image(playback, artistId, fallback_mode="default"):
    try:
        artist_id = artistId
        artist = sp.artist(artist_id)
        images = artist.get("images", [])
        if images:
            show_image_from_url(images[0]["url"])
            return True
    except Exception as e:
        logging.warning(f"⚠️ Fehler beim direkten Artist-Zugriff: {e}")
    
    # Fallback-Suche via aktuellem Track
    try:
        track = playback.get("item")
        if track:
            artist_name = track["artists"][0]["name"]
            logging.debug(f"🔍 Artist-Fallback-Suche für '{artist_name}'")
            search_result = sp.search(q=artist_name, type="artist", limit=1)
            artists = search_result.get("artists", {}).get("items", [])
            if artists:
                images = artists[0].get("images", [])
                if images:
                    show_image_from_url(images[0]["url"])
                    return True
    except Exception as e:
        logging.warning(f"⚠️ Fehler bei Artist-Suche: {e}")

    # Zusätzlicher Fallback in "auto"-Modus: Albumcover
    if fallback_mode == "auto":
        item = playback.get("item")
        track_images = item.get("album", {}).get("images", []) if item else []
        if track_images:
            show_image_from_url(track_images[0]["url"])
            return True

    show_local_fallback("default_artist.jpg")
    return False
    
def process_spotify_update():    
    config = load_config()
    mode = config.get("displayMode", "device")
    initialMode = mode
    try:
        playback = sp.current_playback()
        if not playback:
            logging.warning("⏸ No playback available.")
            show_local_fallback("no_image.jpg")
            return


        if mode == "delete":
            show_local_fallback("delete.jpg")
            return

        if mode == "auto":
            context = playback.get("context", {})        
            if not context:
                logging.warning("⏸ No context available in auto.")
                show_local_fallback("no_image.jpg")
                return

            context_type = context.get("type", "")
            
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
            
            if not item:
                logging.warning("⏸ playback item available.")
                show_local_fallback("no_image.jpg")
                return
                    
            images = item.get("album", {}).get("images", []) if item else []
            if images:
                show_image_from_url(images[0]["url"])
            else:
                show_local_fallback("default_album.jpg")

        elif mode == "playlist":
            try:
                context = playback.get("context", {})  
                if not context:
                    logging.warning("⏸ No context available in playlist.")
                    show_local_fallback("no_image.jpg")
                    return                
                uri = context.get("uri", "")  
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
            artistId = playback.get("item").get("album").get("artists")[0].get("id")  
            show_artist_image(playback, artistId, fallback_mode="auto" if initialMode == "auto" else "default")
        else:
            logging.warning(f"❓ Unbekannter Modus: {mode}")
            show_local_fallback("mode_unknown.jpg")

    except SpotifyException as e:
        if e.http_status == 429:
            retry_after = int(e.headers.get("Retry-After", 5))
            logging.warning(f"⚠️ Rate Limit! Warte {retry_after} Sekunden...")
            show_local_fallback("ratelimit.jpg")
            time.sleep(retry_after)
        else:
            logging.error(f"❌ Fehler in process_once(): {e}")
            show_local_fallback("error.jpg")
    except Exception as e:
        logging.error(f"❌ Fehler in process_once(): {e}")
        show_local_fallback("error.jpg")

def process_once():
    status = get_current_status()
    
    last_spotify_call = 0
    
    while (status != "playing"):
        show_local_fallback(f"{status}.jpg")
        status = get_current_status()
    
    if time.time() - last_spotify_call > 4:
        logging.debug(f"processing spotify update...")
        last_spotify_call = time.time()
        process_spotify_update()
    else:
        logging.debug(f"waiting for next processing time...")

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

# Spotify auth
try:
    auth_manager_old = SpotifyOAuth(
        client_id=config.get("client_id"),
        client_secret=config.get("client_secret"),
        redirect_uri=config.get("redirect_uri"),
        scope="user-read-playback-state user-modify-playback-state user-read-private user-read-email",
        cache_path=Path(__file__).resolve().parent / ".spotify_cache",
        open_browser=False
    )
    
    auth_manager = SpotifyClientCredentials(
        client_id=config.get("client_id"),
        client_secret=config.get("client_secret")
    )

    sp = spotipy.Spotify(
        auth_manager=auth_manager,
        requests_timeout=10,
        retries=3,
        status_forcelist=[500, 502, 503, 504]
    )
except Exception as e:
    logging.error(f"❌ Spotify Auth fehlgeschlagen: {e}")
    exit(1)

start_cleanup_thread(interval_hours=6, days_old=90)

# Normal loop mode
while True:
    process_once()
    time.sleep(0.100)
