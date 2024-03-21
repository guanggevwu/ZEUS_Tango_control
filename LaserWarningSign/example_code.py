import tango

device_name = 'facility/laser_warning_sign/1'
dp = tango.DeviceProxy(device_name)
print(dp.ta1)
print(dp.strobe_light)
