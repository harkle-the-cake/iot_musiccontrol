from flask import Flask, request, render_template, redirect, url_for
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from PIL import Image
from pathlib import Path
from dotenv import load_dotenv
import os
import json

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = Path(__file__).resolve().parent / "static" / "images"
app.config['UPLOAD_FOLDER'].mkdir(parents=True, exist_ok=True)
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # max 5MB
app.config['SETTINGS_FILE'] = Path(__file__).resolve().parent / "config.json"

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

def load_settings():
    if app.config['SETTINGS_FILE'].exists():
        with open(app.config['SETTINGS_FILE'], "r") as f:
            return json.load(f)
    return {"mode": "album", "orientation": "0", "client_id": "", "client_secret": ""}

def save_settings(settings):
    with open(app.config['SETTINGS_FILE'], "w") as f:
        json.dump(settings, f)
    os.environ["SPOTIFY_CLIENT_ID"] = settings["client_id"]
    os.environ["SPOTIFY_CLIENT_SECRET"] = settings["client_secret"]

@app.route("/", methods=["GET", "POST"])
def index():
    settings = load_settings()

    devices = []
    sp = None
    try:
        if settings["client_id"] and settings["client_secret"]:
            sp = Spotify(auth_manager=SpotifyOAuth(
                client_id=settings["client_id"],
                client_secret=settings["client_secret"],
                redirect_uri="http://localhost:8080/callback",
                scope="user-read-playback-state user-read-private user-read-email",
                cache_path=Path(__file__).resolve().parent / ".spotify_cache",
                open_browser=False
            ))
    except Exception as e:
        sp = None

    if request.method == "POST":
        settings["mode"] = request.form.get("mode", "album")
        settings["orientation"] = request.form.get("orientation", "0")
        settings["client_id"] = request.form.get("client_id", "")
        settings["client_secret"] = request.form.get("client_secret", "")
        save_settings(settings)
        return redirect(url_for('index'))

    if settings["mode"] == "device" and sp:
        try:
            devices = sp.devices().get('devices', [])
            for d in devices:
                device_id = d.get("id")
                device_name = d.get("name", "Unnamed")
                image_path = app.config['UPLOAD_FOLDER'] / f"{device_id}.jpg"
                d["image_url"] = url_for('static', filename=f"images/{device_id}.jpg") if image_path.exists() \
                                 else url_for('static', filename="images/default.jpg")
                d["name"] = device_name
        except Exception as e:
            devices = []

    return render_template("index.html", devices=devices, settings=settings)

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
        save_path = app.config['UPLOAD_FOLDER'] / f"{device_id}.jpg"
        image.save(save_path)
        return redirect(url_for('index'))
    except Exception as e:
        return f"Upload failed: {e}", 500

@app.route("/login")
def login():
    settings = load_settings()
    if not settings["client_id"] or not settings["client_secret"]:
        return "Bitte Client ID und Secret zuerst speichern.", 400

    sp_oauth = SpotifyOAuth(
        client_id=settings["client_id"],
        client_secret=settings["client_secret"],
        redirect_uri="http://localhost:8080/callback",
        scope="user-read-playback-state user-modify-playback-state user-read-private user-read-email",
        cache_path=Path(__file__).resolve().parent / ".spotify_cache",
        open_browser=False
    )
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return "Fehler: Kein Code übergeben."

    settings = load_settings()
    sp_oauth = SpotifyOAuth(
        client_id=settings["client_id"],
        client_secret=settings["client_secret"],
        redirect_uri="http://localhost:8080/callback",
        scope="user-read-playback-state user-modify-playback-state user-read-private user-read-email",
        cache_path=Path(__file__).resolve().parent / ".spotify_cache",
        open_browser=False
    )

    try:
        token_info = sp_oauth.get_access_token(code, as_dict=True)
        if token_info:
            return redirect(url_for('index'))
        else:
            return "Token konnte nicht gespeichert werden.", 400
    except Exception as e:
        return f"Fehler bei der Authentifizierung: {e}", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
