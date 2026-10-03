import socket, struct, time
HOST = "192.168.10.111"
PORT = 1004
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
    # 1. Establish connection
    client_socket.connect((HOST, PORT))

    keep_connection = True
    while keep_connection:
        # 2. Send data in bytes
        str_wits_data = """!!
    01082319.024
    01103152.102
    011221.31
    !!"""
        bytes_str_wits_data = str_wits_data.encode('utf-8')

        # bytes_to_send = struct.pack("<I", 2)
        bytes_to_send = struct.pack(f"<I{len(bytes_str_wits_data)}s", len(bytes_str_wits_data), bytes_str_wits_data)
        client_socket.sendall(bytes_to_send)
    
        for i in range(2):
            time.sleep(0.5)

    # bytes_to_send = struct.pack("<I", 3)
    client_socket.sendall(bytes_to_send)

    # 3. Close connection (automatically done by the context manager)
    client_socket.close()
