#!/usr/bin/env python3
import time
import RPi.GPIO as GPIO
from libs import SimpleMFRC522Device2

reader = SimpleMFRC522Device2()

try:
    print("📡 Scanning for RFID tag (CE1)...")
    while True:
        id, text = reader.read_no_block()
        if id:
            print(f"✅ Tag detected – ID: {id}")
            print(f"📄 Text: {text.strip()}")
        else:
            print(".", end="", flush=True)
        time.sleep(0.5)

except KeyboardInterrupt:
    print("\n🔚 Exit via CTRL+C")

finally:
    GPIO.cleanup()

