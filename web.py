from pathlib import Path
from flask import Flask, request, render_template, redirect, url_for
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from PIL import Image
import os
from dotenv import load_dotenv
import json

# Setup
app = Flask(__name__)
base_dir = Path(__file__).resolve().parent
dotenv_path = base_dir / ".env"
load_dotenv(dotenv_path=dotenv_path)

UPLOAD_FOLDER = base_dir / "static" / "images"
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB max

def get_spotify_client():
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI")
    if not client_id or not client_secret or not redirect_uri:
        return None
    try:
        auth = SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope="user-read-playback-state user-read-private user-read-email",
            cache_path=base_dir / ".spotify_cache",
            open_browser=True
        )
        return Spotify(auth_manager=auth)
    except Exception:
        return None

def write_config(data: dict):
    lines = []
    for key, val in data.items():
        lines.append(f"{key}={val}")
    with open(dotenv_path, "w") as f:
        f.write("\n".join(lines))
    load_dotenv(dotenv_path=dotenv_path, override=True)

@app.route("/", methods=["GET"])
def index():
    config = {
        "SPOTIFY_CLIENT_ID": os.getenv("SPOTIFY_CLIENT_ID", ""),
        "SPOTIFY_CLIENT_SECRET": os.getenv("SPOTIFY_CLIENT_SECRET", ""),
        "SPOTIFY_REDIRECT_URI": os.getenv("SPOTIFY_REDIRECT_URI", "http://localhost:8888/callback"),
        "SCREEN_ROTATION": os.getenv("SCREEN_ROTATION", "0"),
        "DISPLAY_MODE": os.getenv("DISPLAY_MODE", "album")
    }

    status = {"ok": False, "track": None}
    sp = get_spotify_client()
    devices = []

    if sp:
        try:
            playback = sp.current_playback()
            if playback and playback.get("item"):
                item = playback["item"]
                name = item.get("name", "Unknown")
                artist = item.get("artists", [{}])[0].get("name", "")
                status = {"ok": True, "track": f"{name} – {artist}"}
        except Exception as e:
            status["track"] = f"Error: {e}"

    if config["DISPLAY_MODE"] == "device" and sp:
        try:
            raw_devices = sp.devices().get("devices", [])
            for d in raw_devices:
                image_path = UPLOAD_FOLDER / f"{d['id']}.jpg"
                devices.append({
                    "id": d["id"],
                    "name": d["name"],
                    "image_url": url_for("static", filename=f"images/{d['id']}.jpg") if image_path.exists() else url_for("static", filename="images/default.jpg")
                })
        except Exception:
            pass

    return render_template("index.html", config=config, devices=devices, status=status)

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
        image = image.crop((left, top, left + min_edge, top + min_edge))
        image = image.resize((240, 240))
        save_path = app.config['UPLOAD_FOLDER'] / f"{device_id}.jpg"
        image.save(save_path)
        return redirect(url_for("index"))
    except Exception as e:
        return f"Upload failed: {e}", 500

@app.route("/update-config", methods=["POST"])
def update_config():
    config = {
        "SPOTIFY_CLIENT_ID": request.form.get("SPOTIFY_CLIENT_ID", "").strip(),
        "SPOTIFY_CLIENT_SECRET": request.form.get("SPOTIFY_CLIENT_SECRET", "").strip(),
        "SPOTIFY_REDIRECT_URI": request.form.get("SPOTIFY_REDIRECT_URI", "").strip(),
        "SCREEN_ROTATION": request.form.get("SCREEN_ROTATION", "0"),
        "DISPLAY_MODE": request.form.get("DISPLAY_MODE", "album")
    }
    write_config(config)
    return redirect(url_for("index"))

@app.route("/callback")
def callback():
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
