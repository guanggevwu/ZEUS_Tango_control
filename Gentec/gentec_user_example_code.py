import tango

device_name = 'test/gentec/1'
dp = tango.DeviceProxy(device_name)
print(dp.main_value)
print(dp.wavelength)
print(dp.attenuator)
