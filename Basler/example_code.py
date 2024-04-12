import tango
import numpy as np
# replace 'test/basler/1' with your device name
dp = tango.DeviceProxy('test/basler/1')
dp.trigger_source = 'software'
dp.send_software_trigger()
while True:
    if dp.is_new_image:
        print(f'Mean intensity of the image is: {np.mean(dp.image)}.')
