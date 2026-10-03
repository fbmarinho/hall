import socket
import struct

HOST = '127.0.0.1'
PORT = 23052

def testar_estrutura(nome_teste: str, payload: bytes) -> bool:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1.5)
        sock.connect((HOST, PORT))
        
        sock.sendall(payload)
        resposta = sock.recv(1024)
        sock.close()
        
        if len(resposta) > 0:
            print(f"[+] SUCESSO [{nome_teste}]: Resposta de {len(resposta)} bytes!")
            print(f"    HEX Resposta: {resposta.hex(' ')}")
            return True
        else:
            print(f"[-] [{nome_teste}]: Servidor desconectou (0 bytes).")
    except Exception as e:
        print(f"[-] [{nome_teste}]: Erro - {e}")
    return False

print("=== Testando Formatos de Cabeçalho do Protocolo ===\n")

# Teste 1: Tamanho do pacote nos primeiros 2 bytes (uint16) + Opcode (uint16)
# Formato: <HHII (Length=16, Opcode=100, Param1=0, Param2=0)
payload_tamanho_16 = struct.pack('<HHII', 16, 100, 0, 0)
testar_estrutura("Length-Prefixed (16 bytes)", payload_tamanho_16)

# Teste 2: Tamanho do payload (12 bytes após o cabeçalho de 4) + Opcode
payload_tamanho_12 = struct.pack('<HHII', 12, 100, 0, 0)
testar_estrutura("Length-Prefixed (12 bytes)", payload_tamanho_12)

# Teste 3: Magic Number / Assinatura de 2 bytes (0x55AA) + Opcode (uint16)
payload_magic = struct.pack('<HHII', 0x55AA, 100, 0, 0)
testar_estrutura("Magic Number (0x55AA)", payload_magic)

# Teste 4: Opcode em 32 bits + Tamanho do Payload em 32 bits
payload_op_len = struct.pack('<IIII', 100, 12, 0, 0)
testar_estrutura("Opcode + Payload Length", payload_op_len)