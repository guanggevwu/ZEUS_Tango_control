import socket
import time

# --- Configuration ---
ESP302_IP = "192.168.131.75"  # Replace with your controller's IP address
ESP302_PORT = 5001  # Default port for Newport Ethernet communication

# --- Connection function ---


try:
    controller_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    controller_socket.settimeout(5)  # Set a timeout for the connection
    controller_socket.connect((ESP302_IP, ESP302_PORT))
    print(f"Successfully connected to ESP302 at {ESP302_IP}")
except socket.error as e:
    print(f"Error connecting to ESP302: {e}")
cmd_string = b"3TP\r"
controller_socket.sendall(cmd_string)
response = controller_socket.recv(1024).decode('ascii').strip()
a = 1
