#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, request, render_template, redirect, url_for
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from PIL import Image
from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

cache_path = Path(__file__).resolve().parent / ".spotify_cache"

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = Path(__file__).resolve().parent / "static" / "images"
app.config['UPLOAD_FOLDER'].mkdir(parents=True, exist_ok=True)
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # max 5MB

# Spotify Auth
sp = Spotify(auth_manager=SpotifyOAuth(
    client_id=os.getenv("SPOTIFY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
    redirect_uri="http://127.0.0.1:8888/callback",
    scope="user-read-playback-state user-read-private user-read-email",
    cache_path = Path(__file__).resolve().parent / ".spotify_cache",
    open_browser=False
))

@app.route("/", methods=["GET"])
def index():
    """Show list of devices and their images"""
    devices = sp.devices().get('devices', [])
    image_dir = app.config['UPLOAD_FOLDER']

    for d in devices:
        device_id = d.get("id")
        device_name = d.get("name", "Unnamed")
        image_path = image_dir / f"{device_id}.jpg"
        d["image_url"] = url_for('static', filename=f"images/{device_id}.jpg") if image_path.exists() \
                         else url_for('static', filename="images/default.jpg")
        d["name"] = device_name

    return render_template("index.html", devices=devices)

@app.route("/upload/<device_id>", methods=["POST"])
def upload(device_id):
    """Handle image upload, crop and resize"""
    if 'file' not in request.files:
        return "No file part", 400

    file = request.files['file']
    if file.filename == '':
        return "No selected file", 400

    try:
        image = Image.open(file.stream).convert("RGB")

        # Crop to center square
        width, height = image.size
        min_edge = min(width, height)
        left = (width - min_edge) // 2
        top = (height - min_edge) // 2
        right = left + min_edge
        bottom = top + min_edge
        image = image.crop((left, top, right, bottom))

        # Resize to 240x240
        image = image.resize((240, 240))

        # Save image
        save_path = app.config['UPLOAD_FOLDER'] / f"{device_id}.jpg"
        image.save(save_path)
        return redirect(url_for('index'))

    except Exception as e:
        return f"Upload failed: {e}", 500

if __name__ == "__main__":
    # Run on HTTP port 80
    app.run(host="0.0.0.0", port=8080)
