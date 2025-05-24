#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import logging
import time
import json
from pathlib import Path
import os
import RPi.GPIO as GPIO
from libs.SimpleMFRC522Device2 import SimpleMFRC522Device2
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

cache_path = Path(__file__).resolve().parent / ".spotify_cache"

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

reader = SimpleMFRC522Device2()

type_map = {
    "a": "album",
    "p": "playlist",
    "d": "device",
    "r": "artist",
    "b": "audiobook"
}

def get_current_context(mode="auto"):
    try:
        playback = sp.current_playback()
        context = playback.get("context") if playback else None

        if not playback or (mode == "auto" and not context):
            return None, None

        if mode == "auto":
            if context and context.get("type") in type_map.values():
                short_type = [k for k, v in type_map.items() if v == context["type"]][0]
                return short_type, context["uri"].split(":")[-1]
            return None, None
        else:
            # fixed mode – write that type regardless of context type
            if context:
                return mode[0], context["uri"].split(":")[-1]
            else:
                return None, None
    except Exception as e:
        logging.error(f"🔍 Failed to fetch current playback: {e}")
        return None, None

def is_effectively_empty(text):
    return not text or all(c in (' ', '\x00', '\n', '\r', '\t') for c in text)

def handle_tag_or_write(text, display_mode):
    if is_effectively_empty(text):
        logging.info(f"🆕 Tag scheint leer zu sein – versuche aktuellen Kontext zu schreiben. Inhalt: {text}")
        t, i = get_current_context(display_mode)
        if t and i:
            json_str = json.dumps({"t": t, "i": i})
            reader.write_no_block(json_str)
            logging.info(f"📝 Geschrieben: {json_str}")
        else:
            logging.warning("⚠️ Kein gültiger Kontext vorhanden – nichts geschrieben.")
        return

    logging.debug(f"📄 Gelesener Tag-Inhalt (roh): {repr(text)}")

    try:
        data = json.loads(text.strip())
    except json.JSONDecodeError as e:
        logging.error(f"❌ Tag-Inhalt ist kein gültiges JSON: {e}")
        return

    t = data.get("t")
    i = data.get("i")

    if not t or not i:
        logging.warning(f"⚠️ Ungültige Struktur: {data}")
        return

    logging.info(f"🎯 Tag: type={t}, id={i}")
    mapped_type = type_map.get(t)
    if not mapped_type:
        logging.warning(f"❓ Unbekannter Typ in Tag: {t}")
        return

    try:
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
            logging.warning(f"⚠️ Kein unterstützter Tag-Typ: {t}")
    except Exception as e:
        logging.error(f"❌ Fehler bei Spotify-Aktion: {e}")

def load_config():
    config_path = Path(__file__).resolve().parent / "config.json"
    if config_path.exists():
        import json
        with open(config_path) as f:
            return json.load(f)
    return {}

def main():
    try:
        config = load_config()
        mode = config.get("rfidMode", "auto")

        while True:
            logging.debug("📡 Waiting for RFID tag...")
            id, text = reader.read_no_block()
            if text:                
                handle_tag_or_write(text, mode)
            else:
                logging.debug("⚠️ No valid context read.")
                
            time.sleep(1)
    finally:
        GPIO.cleanup()


config = load_config()
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=config.get("client_id"),
    client_secret=config.get("client_secret"),
    redirect_uri=config.get("redirect_uri"),
    scope="user-read-playback-state user-modify-playback-state user-read-private user-read-email",
    cache_path=Path(__file__).resolve().parent / ".spotify_cache",
    open_browser=False
))

if __name__ == "__main__":
    main()
