#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, request, render_template, redirect, url_for
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from PIL import Image
from pathlib import Path
import os
import json
from dotenv import load_dotenv

# Konfiguration
BASE_PATH = Path(__file__).resolve().parent
CONFIG_PATH = BASE_PATH / "config.json"
IMAGE_DIR = BASE_PATH / "static" / "images"
IMAGE_DIR.mkdir(parents=True, exist_ok=True)

# Flask App
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = IMAGE_DIR
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # max 5MB

# Konfiguration laden
def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return {
        "client_id": "",
        "client_secret": "",
        "redirect_uri": "",
        "rotation": 0,
        "mode": "device"
    }

# Konfiguration speichern
def save_config(data):
    with open(CONFIG_PATH, "w") as f:
        json.dump(data, f, indent=2)

# Spotify Auth Manager erzeugen
def get_spotify(config):
    if not all([config.get("client_id"), config.get("client_secret"), config.get("redirect_uri")]):
        return None, "⚠️ Spotify Zugangsdaten unvollständig."
    try:
        sp = Spotify(auth_manager=SpotifyOAuth(
            client_id=config["client_id"],
            client_secret=config["client_secret"],
            redirect_uri=config["redirect_uri"],
            scope="user-read-playback-state user-read-private",
            cache_path=BASE_PATH / ".spotify_cache",
            open_browser=True
        ))
        return sp, None
    except Exception as e:
        return None, f"❌ Fehler beim Authentifizieren: {e}"

@app.route("/", methods=["GET"])
def index():
    config = load_config()
    spotify_status = {"ok": False, "message": "❌ Nicht verbunden", "track": None}
    devices = []

    sp, error = get_spotify(config)
    if error:
        spotify_status["message"] = error
    elif sp:
        try:
            playback = sp.current_playback()
            if playback:
                spotify_status["ok"] = True
                item = playback.get("item")
                if item:
                    artist = item['artists'][0]['name']
                    name = item['name']
                    spotify_status["track"] = f"{artist} – {name}"
                else:
                    spotify_status["track"] = "🎵 Keine Wiedergabe"
                spotify_status["message"] = "✅ Verbunden"
            else:
                spotify_status["message"] = "🔇 Keine Wiedergabe"
        except Exception as e:
            spotify_status["message"] = f"❌ Fehler beim Abrufen: {e}"

        # Nur wenn Modus device ist
        if config.get("mode") == "device":
            try:
                devices = sp.devices().get('devices', [])
                for d in devices:
                    device_id = d.get("id")
                    device_name = d.get("name", "Unnamed")
                    image_path = IMAGE_DIR / f"{device_id}.jpg"
                    d["image_url"] = url_for('static', filename=f"images/{device_id}.jpg") if image_path.exists() \
                                     else url_for('static', filename="images/default.jpg")
                    d["name"] = device_name
            except Exception as e:
                devices = []

    return render_template("index.html", config=config, status=spotify_status, devices=devices)

@app.route("/save-config", methods=["POST"])
def save_conf():
    config = {
        "client_id": request.form.get("client_id", ""),
        "client_secret": request.form.get("client_secret", ""),
        "redirect_uri": request.form.get("redirect_uri", ""),
        "rotation": int(request.form.get("rotation", 0)),
        "mode": request.form.get("mode", "device")
    }
    save_config(config)
    return redirect(url_for("index"))

@app.route("/upload/<device_id>", methods=["POST"])
def upload(device_id):
    if 'file' not in request.files:
        return "No file part", 400

    file = request.files['file']
    if file.filename == '':
        return "No selected file", 400

    try:
        image = Image.open(file.stream).convert("RGB")
        width, height = image.size
        min_edge = min(width, height)
        left = (width - min_edge) // 2
        top = (height - min_edge) // 2
        right = left + min_edge
        bottom = top + min_edge
        image = image.crop((left, top, right, bottom))
        image = image.resize((240, 240))
        image.save(IMAGE_DIR / f"{device_id}.jpg")
        return redirect(url_for('index'))

    except Exception as e:
        return f"Upload failed: {e}", 500

@app.route("/login")
def login():
    config = load_config()
    sp_oauth = SpotifyOAuth(
        client_id=config.get("client_id", ""),
        client_secret=config.get("client_secret", ""),
        redirect_uri=config.get("redirect_uri", ""),
        scope="user-read-playback-state user-modify-playback-state user-read-private user-read-email",
        cache_path=Path(__file__).resolve().parent / ".spotify_cache",
        open_browser=True
    )
    print("🔁 Using redirect URI:", config["redirect_uri"])
    print("🔁 Client ID:", config["client_id"][:8], "...")  # zur Vermeidung von Leaks
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@app.route("/callback")
def callback():
    config = load_config()
    sp_oauth = SpotifyOAuth(
        client_id=config.get("client_id", ""),
        client_secret=config.get("client_secret", ""),
        redirect_uri=config.get("redirect_uri", ""),
        scope="user-read-playback-state user-modify-playback-state user-read-private user-read-email",
        cache_path=Path(__file__).resolve().parent / ".spotify_cache",
        open_browser=True
    )
    code = request.args.get("code")
    if not code:
        return "Missing code in callback", 400

    token_info = sp_oauth.get_access_token(code, as_dict=True)
    if token_info:
        return redirect(url_for('index'))
    else:
        return "Authorization failed", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
