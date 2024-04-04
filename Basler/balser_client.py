import tango
import time
import numpy as np

dp = tango.DeviceProxy('test/basler/1')
dp.trigger_source = 'software'
time.sleep(0.5)
dp.get_ready()
time.sleep(0.5)
dp.send_software_trigger()
while True:
    if dp.is_new_image:
        print(np.mean(dp.image))
    time.sleep(0.2)
