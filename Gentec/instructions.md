# Operation

## 1. Start the Gentec-EO devices.

### On the server computer that is connected to a Gentec-EO device.

1. Make sure the device is not used by vendor software.
2. Open a terminal. Enter the following command and replace the path if it is different on the computer:
   cd .\Desktop\zeus_cde\ZEUS_Tango_control\
   .\venv\Scripts\Activate.ps1
   python .\Gentec\menu.py
3. On the popup window, select correct device name (for example "MA1") and "start server". In the terminal, it should show something similar to
   "Genotec-eo device is connected. Model: PH100-Si-HA-OD1. Serial number: 268995"

### On any client computer that is in ZEUS network.

1. Start the Gentec menu as what was done on server computer (step 1 and 2). If you also use the server computer as a client computer, skip this step.
2. On the popup window, select device name (for example "laser/gentec/MA1") and "start Taurus GUI".

## 2. Start the data acquisition script.

## 3. Add new Gentec-EO device to acquisition list.

# Add a Gentec-EO device to Tango control system
