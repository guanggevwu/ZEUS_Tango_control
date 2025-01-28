import serial
import time
dev = serial.Serial(port="COM1", baudrate=19200, bytesize=8, timeout=2, stopbits=serial.STOPBITS_ONE)
# dev.write(b"wrong\r")
# print(dev.readline())
# dev.write(b"TE?\r")
# print(dev.readline())

dev.write(b"1TP\r")
print(dev.readline().decode().replace('\r\n', ''))
dev.write(b"2TP\r")
print(dev.readline().decode().replace('\r\n', ''))

axis1_value = 7.124
dev.write(f"1PA{axis1_value:.4f}\r".encode())
# print(dev.readline())
time.sleep(0.1)
dev.write(f"1ST\r".encode())
print(dev.readline())
dev.write(b"1TP\r")
print(dev.readline())
dev.write(b"2TP\r")
print(dev.readline())
a =1