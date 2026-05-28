import socket
import threading

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# Binding to 0.0.0.0 lets WSL accept the forwarded traffic on port 5555
s.bind( ("0.0.0.0", 5555) )
s.listen()
print("Server is listening on port 5555...")

def coms():
    custom_connection_variable, custom_address_variable = s.accept()
    print(f"Connected by {custom_address_variable}!")
    while True:
        try:
            data = custom_connection_variable.recv(1024)
            if not data: 
                break
            message = data.decode(encoding="utf-8")
            print(f"\nNew message: {message}")
        except:
            break
    print("Connection closed.")

coms_job = threading.Thread(target=coms)
coms_job.start()