import socket
import struct
import time

HOST = '127.0.0.1'
PORT = 23052
TIMEOUT_CLIENTE = 60.0

servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
servidor.bind((HOST, PORT))
servidor.listen(5)

while True:
    conexao_cliente, endereco_cliente = servidor.accept()
    print(f"\n[+] Cliente original conectado de: {endereco_cliente}")
    conexao_cliente.settimeout(TIMEOUT_CLIENTE)
    
    with conexao_cliente:
        try:
            dados_handshake = conexao_cliente.recv(16)    
            opcode, versao, status, reserva = struct.unpack('<IIII', dados_handshake)
            print(f"[*] Handshake Recebido -> Opcode: {opcode}, Versão: {versao}, status: {status}, reserva: {reserva}")
        except socket.timeout:
                print("[!] Timeout: O cliente não enviou o próximo comando após o handshake.")
        except Exception as e:
                print(f"[!] Erro: {e}")