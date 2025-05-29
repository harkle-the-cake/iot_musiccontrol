#!/usr/bin/env python3
from flask import Flask, request, jsonify
from threading import Lock, Timer
import time

app = Flask(__name__)

# Interner Zustand
status = {"value": "playing", "timestamp": time.time()}
lock = Lock()
reset_timer = None
RESET_DELAY = 3  # Sekunden

def reset_status():
    global status
    with lock:
        status["value"] = "playing"
        status["timestamp"] = time.time()

def schedule_reset():
    global reset_timer
    if reset_timer:
        reset_timer.cancel()
    reset_timer = Timer(RESET_DELAY, reset_status)
    reset_timer.start()

@app.route("/status", methods=["POST"])
def set_status():
    data = request.get_json()
    new_status = data.get("status")

    if new_status not in ["playing", "writing", "success", "error", "deleting","reading"]:
        return jsonify({"error": "Invalid status"}), 400

    with lock:
        status["value"] = new_status
        status["timestamp"] = time.time()

    if new_status != "playing":
        schedule_reset()

    return jsonify(success=True)

@app.route("/status", methods=["GET"])
def get_status():
    with lock:
        return jsonify(status)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5055)
