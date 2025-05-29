#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import time
import json
import logging
from pathlib import Path
import os
import RPi.GPIO as GPIO
from dotenv import load_dotenv
from libs.SimplePN532 import SimplePN532  # deine angepasste Klasse
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import requests

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

# Konfiguration laden
def load_config():
    config_path = Path(__file__).resolve().parent / "config.json"
    if config_path.exists():
        with open(config_path) as f:
            import json
            return json.load(f)
    return {"mode": "uhknown"}

config = load_config()
# Spotify auth
try:
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=config.get("client_id"),
        client_secret=config.get("client_secret"),
        redirect_uri=config.get("redirect_uri"),
        scope="user-read-playback-state user-modify-playback-state user-read-private user-read-email",
        cache_path=Path(__file__).resolve().parent / ".spotify_cache",
        open_browser=False
    ))
except Exception as e:
    logging.error(f"❌ Spotify Auth fehlgeschlagen: {e}")
    exit(1)

# Tag-Kürzel → Spotify Typ
type_map = {
    "a": "album",
    "p": "playlist",
    "d": "device",
    "r": "artist",
    "b": "audiobook"
}
reverse_type_map = {v: k for k, v in type_map.items()}

reader = SimplePN532(debug=False)


def update_status(status_value: str):
    try:
        r = requests.post("http://127.0.0.1:5055/status", json={"status": status_value}, timeout=0.5)
        if logging.getLogger().isEnabledFor(logging.DEBUG):
            logging.debug(f"📡 Status gesetzt: {status_value} (HTTP {r.status_code})")
    except Exception as e:
        if logging.getLogger().isEnabledFor(logging.DEBUG):
            logging.debug(f"⚠️ Status-Post fehlgeschlagen: {e}")

def get_current_context():
    try:
        playback = sp.current_playback()
        context = playback.get("context") if playback else None
        if context and context.get("type") in reverse_type_map:
            short_type = reverse_type_map[context["type"]]
            return short_type, context["uri"].split(":")[-1]
        return None, None
    except Exception as e:
        logging.warning(f"⚠️ Konnte Kontext nicht laden: {e}")
        return None, None

def handle_existing_tag(tag_data):
    try:
        data = json.loads(tag_data)
        t = data.get("t")
        i = data.get("i")
        if not t or not i:
            raise ValueError("⚠️ Ungültige Tag-Daten")
        logging.debug(f"🎯 Tag erkannt: Type={t}, ID={i}")
        if t == "p":
            sp.start_playback(context_uri=f"spotify:playlist:{i}")
        elif t == "a":
            sp.start_playback(context_uri=f"spotify:album:{i}")
        elif t == "b":
            sp.start_playback(context_uri=f"spotify:audiobook:{i}")
        elif t == "r":
            top_tracks = sp.artist_top_tracks(i, country="DE")
            uris = [track["uri"] for track in top_tracks["tracks"]]
            if uris:
                sp.start_playback(uris=uris)
        elif t == "d":
            sp.transfer_playback(i, force_play=True)
        else:
            logging.warning("❓ Unbekannter Typ im Tag")
    except Exception as e:
        logging.error(f"❌ Fehler bei der Auswertung des Tags: {e}")

def main():
    logging.info("📡 RFID-Service gestartet...")
    lastTag = ""
    try:
        while True:
            id, text = reader.read_tag()
            if not id:
                time.sleep(0.5)
                continue
            
            mode = config.get("rfidMode")
            
            if mode == "delete":
                if text:                    
                    update_status("deleting")
                    logging.info(f"🗑 Tag {id} wird gelöscht.")
                    reader.write_tag("")
                    id, text = reader.read_tag()
                    logging.info(f"🗑 Tag {id} Inhalt: {text}")
                    if not text:
                        update_status("success")
                    else:
                        update_status("error")
                continue
            
            if text:
                text = text.strip()
                if (lastTag==text):
                    logging.debug(f"📄 Not switching to: {text} since no change")
                else:
                    logging.info(f"📄 Gelesener Tag: {text}")                        
                    handle_existing_tag(text)
                    lastTag=text
            else:
                logging.debug(f"📄 Gelesener Tag leer")
                update_status("writing")
                t, i = get_current_context()
                if not t or not i:
                    logging.warning("🚫 Kein gültiger Kontext zum Schreiben")
                    continue
                # Bei festem Modus überschreiben
                if mode in type_map and mode != "auto":
                    t = reverse_type_map.get(mode, t)
                data = json.dumps({"t": t, "i": i})
                id, written = reader.write_tag(data)
                
                if written: 
                    id, text = reader.read_tag()
                    logging.debug(f"📝 Verifiziert: {text}")
                    logging.info(f"📝 Geschrieben: {data}")
                    update_status("success")
                else:                    
                    logging.error(f"📝 Daten nicht geschrieben: {data}")
                    update_status("error")
                        
            time.sleep(1)
    finally:
        GPIO.cleanup()

if __name__ == "__main__":
    main()