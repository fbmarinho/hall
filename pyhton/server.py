import socket
import struct
import time

HOST = '127.0.0.1'
PORT = 23052
TIMEOUT_CLIENTE = 60.0

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def iniciar_servidor_avancado():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as servidor:
        servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        servidor.bind((HOST, PORT))
        servidor.listen(5)
        print(f"[*] Servidor de Testes aguardando o cliente comercial na porta {PORT}...")

        while True:
            conexao_cliente, endereco_cliente = servidor.accept()
            print(f"\n[+] Cliente original conectado de: {endereco_cliente}")
            conexao_cliente.settimeout(TIMEOUT_CLIENTE)
            
            with conexao_cliente:
                try:
                    # 1. Recebe os 16 bytes de Handshake do cliente original
                    dados_handshake = conexao_cliente.recv(16)
                    if not dados_handshake or len(dados_handshake) < 16:
                        print("[-] Cliente enviou handshake inválido ou desconectou.")
                        continue
                    
                    opcode, versao, status, reserva = struct.unpack('<IIII', dados_handshake)
                    print(f"[*] Handshake Recebido -> Opcode: {opcode}, Versão: {versao}")

                    # 2. Gera a resposta correta com o Unix Timestamp atual do sistema
                    timestamp_atual = int(time.time()) # Pega o tempo Unix atual (ex: 1790877043)
                    
                    # Monta a resposta exatamente como o servidor real faria:
                    # Opcode 101, Status 0, Timestamp Atual, Reserva 0
                    resposta_handshake = struct.pack('<IIII', 101, 0, timestamp_atual, 0)
                    
                    print(f"[*] Respondendo ao cliente com o Timestamp: {timestamp_atual}")
                    conexao_cliente.sendall(resposta_handshake)
                    print("[+] Resposta enviada! Aguardando a PRÓXIMA mensagem do cliente original...")

                    # 3. CAPTURA O PRÓXIMO PASSO DO PROTOCOLO
                    # Como o cliente original recebeu o que queria, ele vai enviar o próximo comando comercial
                    proximos_dados = conexao_cliente.recv(4096)

                    if len(proximos_dados) >= 74:

                        op, sub_op, param, payload_len = struct.unpack('<IIII', proximos_dados[:16])

                        # Isolando o Payload (Restante dos bytes)
                        payload = proximos_dados[16:]
                        len_exe = struct.unpack('<I', payload[0:4])[0]
                        nome_exe = payload[4:4+len_exe].decode('ascii', errors='replace').strip('\x00')
                        idx_host = 4 + len_exe
                        len_host = struct.unpack('<I', payload[idx_host:idx_host+4])[0]
                        hostname = payload[idx_host+4:idx_host+4+22].decode('ascii', errors='replace').strip('\x00')

                        idx_user = idx_host + 4 + 22
                        len_user = struct.unpack('<I', payload[idx_user:idx_user+4])[0]
                        username = payload[idx_user+4:idx_user+4+8].decode('ascii', errors='replace').strip('\x00')

                        # Exibição Amigável Estruturada
                        print(f" {Colors.BOLD}[Cabeçalho do Pacote]{Colors.RESET}")
                        print(f"  └─ Opcode Base   : {op}")
                        print(f"  └─ Sub-Opcode    : {sub_op} (Comando de Identificação)")
                        print(f"  └─ Parâmetro     : {param}")
                        print(f"  └─ Tam. Payload  : {payload_len} bytes")
                        print(f"\n {Colors.BOLD}[Identidade da Máquina Cliente]{Colors.RESET}")
                        print(f"  └─ Executável    : {Colors.OKBLUE}{nome_exe}{Colors.RESET} (Tamanho declarado: {len_exe})")
                        print(f"  └─ Nome do PC    : {Colors.OKBLUE}{hostname}{Colors.RESET}")
                        print(f"  └─ Usuário OS    : {Colors.OKBLUE}{username}{Colors.RESET}")

                    if not proximos_dados:
                        print("[-] O cliente fechou a conexão após o handshake.")
                        continue

                    print(f"\n[!] NOVA MENSAGEM CAPTURADA ({len(proximos_dados)} bytes):")
                    print("-" * 50)
                    print("[HEXADECIMAL]")
                    print(proximos_dados.hex(sep=' '))
                    print("\n[TEXTO / ASCII]")
                    print(proximos_dados.decode('utf-8', errors='replace'))
                    print("-" * 50)

                except socket.timeout:
                    print("[!] Timeout: O cliente não enviou o próximo comando após o handshake.")
                except Exception as e:
                    print(f"[!] Erro: {e}")

if __name__ == "__main__":
    iniciar_servidor_avancado()
