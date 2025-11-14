import time
import board
import busio
import digitalio
import usb_hid
import pwmio

from mfrc522 import MFRC522
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS

DEBUG = False

# =========================
# KONFIG
# =========================

BUZZER_PIN = board.GP13

# RDM6300 Pins
RDM_UART_TX = board.GP0
RDM_UART_RX = board.GP1
RDM_EN_PIN  = board.GP10   # 2N2222 Basis

COOLDOWN_MS = 2000
PHASE_DURATION_MS = 250  # 0,25s pro Leser

# =========================
# BUZZER (Software PWM)
# =========================

def play_beep(freq, duration):
    try:
        buzzer = pwmio.PWMOut(BUZZER_PIN, frequency=freq, duty_cycle=32768)
        time.sleep(duration)
        buzzer.deinit()
    except Exception as e:
        print("Buzzer Error:", e)

# Unterschiedliche Beeps pro Reader
def beep_rc522():
    play_beep(3000, 0.1)  # RC522 höherer Erfolgston
    play_beep(2000, 0.1)
    play_beep(3000, 0.1)

def beep_rdm():
    play_beep(2000, 0.1)  # RDM6300 tieferer Erfolgston
    play_beep(3000, 0.1)

# =========================
# USB Keyboard
# =========================

kbd = Keyboard(usb_hid.devices)
layout = KeyboardLayoutUS(kbd)

def send_uid_as_keyboard(uid_str: str):
    if not uid_str:
        return
    layout.write(uid_str)
    kbd.send(Keycode.ENTER)

# =========================
# RDM6300
# =========================

rdm_en = digitalio.DigitalInOut(RDM_EN_PIN)
rdm_en.direction = digitalio.Direction.OUTPUT
rdm_en.value = False

rdm_uart = busio.UART(RDM_UART_TX, RDM_UART_RX, baudrate=9600, timeout=0.05)

RDM_BUFFER_SIZE = 14
rdm_buffer = bytearray(RDM_BUFFER_SIZE)
rdm_buf_i = 0
rdm_last_byte_ms = 0
RDM_BYTE_TIMEOUT_MS = 200

rdm_last_read_time = 0

def rdm_on():
    rdm_en.value = True

def rdm_off():
    rdm_en.value = False

def process_rdm(now_ms: int):
    global rdm_buf_i, rdm_last_byte_ms, rdm_last_read_time

    if rdm_buf_i > 0 and (now_ms - rdm_last_byte_ms) > RDM_BYTE_TIMEOUT_MS:
        rdm_buf_i = 0

    data = rdm_uart.read(32)
    if not data:
        return

    for b in data:
        rdm_last_byte_ms = now_ms

        if b == 0x02:
            rdm_buf_i = 0

        if rdm_buf_i < RDM_BUFFER_SIZE:
            rdm_buffer[rdm_buf_i] = b
            rdm_buf_i += 1
        else:
            rdm_buf_i = 0
            continue

        if b == 0x03 and rdm_buf_i == RDM_BUFFER_SIZE:
            tag_chars = rdm_buffer[1:11]

            try:
                tag_str = "".join(chr(c) for c in tag_chars)
            except:
                tag_str = ""

            if tag_str and (now_ms - rdm_last_read_time) >= COOLDOWN_MS:
                print("RDM6300 Tag:", tag_str)
                rdm_last_read_time = now_ms
                send_uid_as_keyboard(tag_str)
                beep_rdm()

            rdm_buf_i = 0

# =========================
# RC522 (13,56 MHz)
# =========================

spi = busio.SPI(clock=board.GP2, MOSI=board.GP3, MISO=board.GP4)

cs = digitalio.DigitalInOut(board.GP5)
rst = digitalio.DigitalInOut(board.GP6)

rc522 = MFRC522(spi, cs, rst)

last_rc522_uid = None
last_rc522_time = 0

def process_rc522():
    global last_rc522_uid, last_rc522_time

    stat, _ = rc522.request(rc522.REQIDL)
    if stat != rc522.OK:
        return

    stat, uid = rc522.anticoll()
    if stat != rc522.OK:
        return

    if not isinstance(uid, (list, tuple)) or len(uid) < 4:
        return

    uid_str = "".join("{:02X}".format(b) for b in uid)

    now = time.monotonic()
    if uid_str == last_rc522_uid and (now - last_rc522_time) < 1.0:
        return

    last_rc522_uid = uid_str
    last_rc522_time = now

    print("RC522 UID:", uid_str)
    send_uid_as_keyboard(uid_str)
    beep_rc522()

# =========================
# MAIN LOOP
# =========================

print("Universal RFID Keyboard Reader (RC522 + RDM6300) startet...")

phase = 0
phase_start_ms = int(time.monotonic() * 1000)

while True:
    now_ms = int(time.monotonic() * 1000)

    # Phase umschalten
    if now_ms - phase_start_ms >= PHASE_DURATION_MS:
        phase = 1 - phase
        phase_start_ms = now_ms

        if phase == 0:
            rdm_off()
        else:
            rdm_on()

    if phase == 0:
        process_rc522()
    else:
        process_rdm(now_ms)

    time.sleep(0.01)
