import storage
import usb_cdc

# USB Laufwerk deaktivieren
storage.disable_usb_drive()

# COM-Port deaktivieren
usb_cdc.disable()
