import socket
import struct
import time

HOST = '0.0.0.0'
PORT = 52106 #NPDET
TIMEOUT_CLIENTE = 10.0

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
            
            while True:
                resposta = conexao_cliente.recv(1024)    
                print(f"[+] Handshake recebido do cliente: {resposta}")

                if not resposta:
                    print("[-] O cliente encerrou a conexão.")
                    break

                conexao_cliente.sendall(resposta)
                print(f"[+] Resposta enviada de volta para o cliente: {resposta}")

        except socket.timeout:
                print("[!] Timeout: O cliente não enviou o próximo comando após o handshake.")
        except Exception as e:
                servidor.close()
                print(f"[!] Erro: {e}")
        finally:
            print("[+] Conexão com o cliente encerrada.")
