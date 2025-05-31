#!/usr/bin/env python3
from flask import Flask, request, jsonify
from threading import Lock, Timer
import logging
import time

app = Flask(__name__)

# Interner Zustand
status = {"value": "playing", "timestamp": time.time()}
lock = Lock()
reset_timer = None
RESET_DELAY = 3  # Sekunden

# Logging
# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

logging.getLogger('werkzeug').setLevel(logging.WARNING)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("requests").propagate = True
logging.getLogger("urllib3").setLevel(logging.WARNING)
# Disable all child loggers of urllib3, e.g. urllib3.connectionpool
logging.getLogger("urllib3").propagate = True

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
