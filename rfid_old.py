#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import logging
import time
import json
from pathlib import Path
import os
import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

cache_path = Path(__file__).resolve().parent / ".spotify_cache"

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

reader = SimpleMFRC522()

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

def handle_tag(tag_json):
    # check current playback context
    try:
        playback = sp.current_playback()
        current_type = None
        current_id = None
        if playback and playback.get("context"):
            uri = playback["context"].get("uri", "")
            parts = uri.split(":")
            if len(parts) >= 3:
                current_type = parts[1]
                current_id = parts[2]
    except Exception as e:
        logging.warning(f"⚠️ Cannot determine current context: {e}")
        
    try:
        data = json.loads(tag_json)
        t, i = data.get("t"), data.get("i")
        if not t or not i:
            raise ValueError("Invalid tag structure")

        logging.info(f"🎯 Tag: type={t}, id={i}")
        mapped_type = type_map.get(t)
        logging.info(f"🎯 current Tag: type={mapped_type}, id={i}")
        logging.info(f"🎯 Spotify context: type={current_type}, id={current_id}")
        if mapped_type == current_type and current_id == i:
            logging.info("🔁 Tag matches current playback – nothing to change.")
            return

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
            logging.warning("❓ Unknown tag type.")
    except Exception as e:
        logging.error(f"❌ Failed to interpret tag: {e}")

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
            logging.info("📡 Waiting for RFID tag...")
            id, text = reader.read()
            text = text.strip()

            if mode == "delete":
                if text:
                    logging.info(f"🗑 Tag will be deleted (content: {text})")
                    reader.write_no_block("")  # clear tag
                    logging.info("✅ Tag erased.")
                else:
                    logging.info("💡 Tag already empty.")
            else:
                if text:
                    logging.info(f"📄 Read tag content: {text}")
                    handle_tag(text)
                else:
                    logging.info("🆕 Empty tag – writing current context...")
                    t, i = get_current_context()
                    if t and i:
                        json_str = json.dumps({"t": t, "i": i})
                        reader.write_no_block(json_str)
                        logging.info(f"📝 Wrote tag: {json_str}")
                    else:
                        logging.warning("⚠️ No valid context to write.")

            time.sleep(2)
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
