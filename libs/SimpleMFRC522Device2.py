# Code by Simon Monk https://github.com/simonmonk/

from . import MFRC522
import RPi.GPIO as GPIO

class SimpleMFRC522Device2:

  READER = None

  KEY = [0xFF,0xFF,0xFF,0xFF,0xFF,0xFF]
  BLOCK_ADDRS = [8, 9, 10]

  def __init__(self):
    self.READER = MFRC522.MFRC522(bus=0, device=1, spd=1000000, pin_rst=15, debugLevel='WARNING')

  def read(self):
      id, text = self.read_no_block()
      while not id:
          id, text = self.read_no_block()
      return id, text

  def read_id(self):
    id = self.read_id_no_block()
    while not id:
      id = self.read_id_no_block()
    return id

  def read_id_no_block(self):
    (status, TagType) = self.READER.MFRC522_Request(self.READER.PICC_REQIDL)
    if status != self.READER.MI_OK:
        return None
    (status, uid) = self.READER.MFRC522_Anticoll()
    if status != self.READER.MI_OK:
        return None
    return self.uid_to_num(uid)

  def read_no_block(self):
    (status, TagType) = self.READER.MFRC522_Request(self.READER.PICC_REQIDL)
    if status != self.READER.MI_OK:
        return None, None
    (status, uid) = self.READER.MFRC522_Anticoll()
    if status != self.READER.MI_OK:
        return None, None
    id = self.uid_to_num(uid)
    self.READER.MFRC522_SelectTag(uid)
    status = self.READER.MFRC522_Auth(self.READER.PICC_AUTHENT1A, 11, self.KEY, uid)
    data = []
    text_read = ''
    if status == self.READER.MI_OK:
        for block_num in self.BLOCK_ADDRS:
            block = self.READER.MFRC522_Read(block_num)
            if block:
                        data += block
        if data:
             text_read = ''.join(chr(i) for i in data)
    self.READER.MFRC522_StopCrypto1()
    return id, text_read

  def write(self, text):
      id, text_in = self.write_no_block(text)
      while not id:
          id, text_in = self.write_no_block(text)
      return id, text_in

  def write_no_block(self, text):
    (status, TagType) = self.READER.MFRC522_Request(self.READER.PICC_REQIDL)
    if status != self.READER.MI_OK:
        return None, None

    (status, uid) = self.READER.MFRC522_Anticoll()
    if status != self.READER.MI_OK:
        return None, None

    id = self.uid_to_num(uid)
    self.READER.MFRC522_SelectTag(uid)
    status = self.READER.MFRC522_Auth(self.READER.PICC_AUTHENT1A, 11, self.KEY, uid)

    if status != self.READER.MI_OK:
        print("❌ Authentifizierung fehlgeschlagen.")
        self.READER.MFRC522_StopCrypto1()
        return None, None

    # Daten vorbereiten
    full_text = text.ljust(len(self.BLOCK_ADDRS) * 16)
    data = bytearray(full_text.encode("ascii"))

    for i, block_num in enumerate(self.BLOCK_ADDRS):
        chunk = data[i*16:(i+1)*16]
        write_status = self.READER.MFRC522_Write(block_num, list(chunk))
        if write_status != self.READER.MI_OK:
            print(f"❌ Schreibfehler in Block {block_num}")
            self.READER.MFRC522_StopCrypto1()
            return None, None

    self.READER.MFRC522_StopCrypto1()
    return id, full_text.strip()


  def uid_to_num(self, uid):
      n = 0
      for i in range(0, 5):
          n = n * 256 + uid[i]
      return n