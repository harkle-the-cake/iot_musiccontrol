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

    def read_tag(self, timeout=0.5, strict=False):
        uid = self.pn532.read_passive_target(timeout=timeout)
        if not uid:
            return None, None

        data = bytearray()
        for i in range(self.block_count):
            block = self.pn532.ntag2xx_read_block(self.start_block + i)
            retry_counter = 0
            
            while (block is None and retry_counter < 10):
                block = self.pn532.ntag2xx_read_block(self.start_block + i)
                retry_counter = retry_counter + 1
                
            if block is None:
                if strict:
                    return uid, None
                else:
                    logging.warning(f"⚠️ Block {self.start_block + i} konnte nicht gelesen werden.")
                    data.extend(b"\x00\x00\x00\x00")
            else:
                data.extend(block)

        return uid, data.rstrip(b"\x00").decode("ascii", errors="replace")

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
