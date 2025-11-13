# Universal RFID Keyboard Reader  
Dual Reader: MFRC522 (13.56 MHz) + RDM6300 (125 kHz)

## Overview
This project turns a Raspberry Pi Pico into a pure USB HID keyboard that outputs RFID tag IDs as keystrokes.  
It supports **both 13.56 MHz (RC522)** and **125 kHz (RDM6300)** readers, running in an alternating phase mode.  
If the RC522 is not detected during boot, the device automatically falls back to **RDM-Only Mode**.

---

## ✨ Features
- Dual RFID reader support (RC522 + RDM6300)
- Automatic fallback to RDM-only mode if no RC522 detected
- HID Keyboard output (no serial or storage)
- Acoustic feedback with different tones per reader
- Debounce logic to avoid repeated scans
- Recovery mode available via `BOOTSEL` + UF2 flashing

---

## 🛠 Hardware Wiring

### MFRC522 (SPI)
| MFRC522 | Pico |
|---------|------|
| SDA (SS) | GP5 |
| SCK | GP2 |
| MOSI | GP3 |
| MISO | GP4 |
| RST | GP6 |
| 3.3V | 3V3 |
| GND | GND |

### RDM6300 (UART)
| RDM6300 | Pico |
|---------|------|
| TX | GP1 |
| 5V | VBUS |
| GND | 2N2222 ->  Collector|

### 2N2222 (Enable RDM6300)
| Comment | Pin |
|---------|------|
| Collector | RDM6300 GND |
| Base | 10k -> GP10 |
| Emitter | GND && 100k -> Base (Pulldown) |

### Buzzer
| Component | Pin |
|-----------|-----|
| Piezo Buzzer + | GP16 |
| Piezo Buzzer - | GND |

A 2N2222 transistor + 10k base resistor + 100k pull-down should be used to control RDM6300’s enable pin.

---

## 🔧 Setup Instructions

### 1. Install CircuitPython
1. Hold **BOOTSEL**
2. Connect the Pico to USB
3. Flash the latest CircuitPython UF2 for RP2040  
   https://circuitpython.org/board/raspberry_pi_pico/

The board will reboot into a storage device named **CIRCUITPY**.

---

### 2. Install Adafruit HID Library
Create a `lib` folder on CIRCUITPY.  
Download the Adafruit HID library bundle:

👉 **https://github.com/adafruit/Adafruit_CircuitPython_HID**

Copy the folder:

```
adafruit_hid/
```

into:

```
CIRCUITPY/lib/
```

---

### 3. Install MFRC522 driver
Place `lib/mfrc522.py` into:

```
CIRCUITPY/lib/
```

(This project uses the open‑source MFRC522 driver by **mziter**, modified for CircuitPython compatibility.)

---

### 3. Copy the project files
Place these files onto **CIRCUITPY**:

- `code.py` → main program  
- `boot.py` → HID-only configuration  

---

## ♻ Recovery Mode
If HID-only mode disables storage, you can recover:

1. Hold **BOOTSEL**
2. Plug in the Pico  
3. Flash a fresh CircuitPython UF2  
4. Access the mass storage normally  
5. Restore files

---

## 🧪 Operation
After boot:

- RC522 presence check runs  
- If found → alternating scanning RC522/RDM6300  
- If not found → RDM-only mode  
- Detected tag UIDs are typed as keyboard input  
- Each reader has its own beep sequence

---

## 📜 Licenses

### Project License
MIT License — free to use with attribution.  
Author: **Thomas Störzner (Flash2over)**  
Date: **November 2025**

### Third-Party Code Notice (Required)
This project includes modified code originally published by:

**domdfcoding**, MFRC522 Driver (MIT License)  
Source: https://github.com/domdfcoding/circuitpython-mfrc522

All modifications and adaptations for:
- Raspberry Pi Pico  
- Dual-reader mode  
- Debounce logic  
- Timing improvements  
were made by **Thomas Störzner (Flash2over)**.

---

## 👍 Status
Stable and production-ready.  
Fully HID-only and requires no drivers.

Enjoy your plug‑and‑play RFID keyboard reader!
