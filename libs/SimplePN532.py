# simple_pn532.py

import board
import busio
import logging
from digitalio import DigitalInOut
from adafruit_pn532.i2c import PN532_I2C

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

class SimplePN532:
    def __init__(self, start_block=4, block_count=12, debug=False):
        """Initialisiert die PN532-Kommunikation via I2C."""
        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.pn532 = PN532_I2C(self.i2c, debug=debug)
        self.pn532.SAM_configuration()
        self.start_block = start_block
        self.block_count = block_count  # Standard: 12 Blöcke × 4 Byte = 48 Byte

   def read_tag(self, timeout=2.0, retry_delay=0.1):
    """
    Liest den Inhalt eines Tags (ASCII) robust, bis alle Blöcke erfolgreich gelesen wurden
    oder ein Timeout überschritten ist.
    Gibt (UID, Text) zurück oder (None, None) bei Nichterkennung.
    """
    start_time = time.time()
    uid = None

    while (time.time() - start_time) < timeout:
        uid = self.pn532.read_passive_target(timeout=0.5)
        if not uid:
            continue

        all_blocks = {}
        while len(all_blocks) < self.block_count:
            for i in range(self.block_count):
                if i in all_blocks:
                    continue
                block_index = self.start_block + i
                block = self.pn532.ntag2xx_read_block(block_index)
                if block:
                    all_blocks[i] = block
                else:
                    logging.debug(f"⚠️ Block {block_index} konnte nicht gelesen werden – neuer Versuch...")
            time.sleep(retry_delay)

        # Nach erfolgreichem Lesen aller Blöcke:
        data = bytearray()
        for i in range(self.block_count):
            data.extend(all_blocks[i])
        text = data.rstrip(b"\x00").decode("utf-8", errors="replace")
        return uid, text

    return None, None  # Timeout erreicht


    def write_tag(self, text, timeout=0.5):
        """Schreibt einen ASCII-Text auf das Tag. Rückgabe: (UID, success:bool)"""
        uid = self.pn532.read_passive_target(timeout=timeout)
        if not uid:
            return None, False

        encoded = text.encode("ascii")[:self.block_count * 4]
        padded = encoded.ljust(self.block_count * 4, b"\x00")

        for i in range(self.block_count):
            block_data = padded[i*4:(i+1)*4]
            success = self.pn532.ntag2xx_write_block(self.start_block + i, block_data)
            if not success:
                return uid, False
        return uid, True
