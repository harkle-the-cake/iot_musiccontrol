#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, request, render_template, redirect, url_for
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from PIL import Image
from pathlib import Path
import os
import json
from dotenv import load_dotenv, set_key

# Initialisierung
base_path = Path(__file__).resolve().parent
env_path = base_path / ".env"
config_path = base_path / "config.json"
image_path = base_path / "static" / "images"
image_path.mkdir(parents=True, exist_ok=True)

load_dotenv(dotenv_path=env_path)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = image_path
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # max 5MB

# Spotify Auth
sp = Spotify(auth_manager=SpotifyOAuth(
    client_id=os.getenv("SPOTIFY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
    redirect_uri="http://127.0.0.1:8888/callback",
    scope="user-read-playback-state user-read-private user-read-email",
    cache_path=base_path / ".spotify_cache",
    open_browser=False
))

# -- Hilfsfunktionen --

def load_config():
    if config_path.exists():
        with open(config_path) as f:
            return json.load(f)
    return {
        "mode": "album",
        "rotation": 0
    }

def save_config(config):
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

# -- Routen --

@app.route("/", methods=["GET"])
def index():
    config = load_config()
    current_mode = config.get("mode", "album")
    current_rotation = config.get("rotation", 0)
    client_id = os.getenv("SPOTIFY_CLIENT_ID", "")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET", "")

    devices = sp.devices().get('devices', [])
    for d in devices:
        d_id = d.get("id")
        d["image_url"] = url_for('static', filename=f"images/{d_id}.jpg") \
                         if (image_path / f"{d_id}.jpg").exists() \
                         else url_for('static', filename="images/default.jpg")
    return render_template("index.html",
                           devices=devices,
                           current_mode=current_mode,
                           client_id=client_id,
                           client_secret=client_secret,
                           current_rotation=current_rotation)

@app.route("/upload/<device_id>", methods=["POST"])
def upload(device_id):
    if 'file' not in request.files:
        return "No file part", 400
    file = request.files['file']
    if file.filename == '':
        return "No selected file", 400
    try:
        img = Image.open(file.stream).convert("RGB")
        w, h = img.size
        edge = min(w, h)
        img = img.crop(((w - edge) // 2, (h - edge) // 2, (w + edge) // 2, (h + edge) // 2))
        img = img.resize((240, 240))
        img.save(image_path / f"{device_id}.jpg")
        return redirect(url_for('index'))
    except Exception as e:
        return f"Upload failed: {e}", 500

@app.route("/set_mode", methods=["POST"])
def set_mode():
    mode = request.form.get("mode")
    if mode not in ["album", "playlist_or_artist", "device", "delete_mode"]:
        return "Invalid mode", 400
    config = load_config()
    config["mode"] = mode
    save_config(config)
    return redirect(url_for('index'))

@app.route("/save_settings", methods=["POST"])
def save_settings():
    new_client_id = request.form.get("client_id", "").strip()
    new_client_secret = request.form.get("client_secret", "").strip()
    rotation = int(request.form.get("rotation", "0"))

    if new_client_id:
        set_key(env_path, "SPOTIFY_CLIENT_ID", new_client_id)
    if new_client_secret:
        set_key(env_path, "SPOTIFY_CLIENT_SECRET", new_client_secret)

    config = load_config()
    config["rotation"] = rotation
    save_config(config)

    return redirect(url_for('index'))

# -- Start --
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
