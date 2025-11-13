import storage
import usb_cdc

# Wieder normaler Modus
storage.enable_usb_drive()
usb_cdc.enable(console=True, data=True)