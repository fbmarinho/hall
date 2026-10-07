import socket
import struct
import time
import math
from datetime import datetime

HOST = '0.0.0.0'
PORT = 52106

def agora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

def hex_dump(data):
    return " ".join(f"{b:02X}" for b in data)

def montar_pacote_voltagens(contador, num_canais=8):
    """
    Monta a resposta simulada contendo 8 valores de voltagem em ponto flutuante (Little-Endian).
    Vamos simular valores dinâmicos (ex: senóides defasadas para cada canal) 
    para que a tela do cliente reaja visualmente.
    """
    valores_floats = []
    for i in range(num_canais):
        # Cria uma variação diferente para cada canal usando seno com fases distintas
        # Variando entre 0.0V e 10.0V por exemplo
        fase = contador * 0.2 + (i * 0.5)
        voltagem = 5.0 + 4.0 * math.sin(fase) 
        valores_floats.append(float(voltagem))

    # Empacota os 8 floats em formato Little-Endian ('<8f')
    payload_floats = struct.pack('<8f', *valores_floats)
    
    # Estrutura candidata para a resposta:
    # [4 bytes de tamanho] + [1 byte de opcode/status] + [32 bytes dos 8 floats]
    # Tamanho total do payload após o cabeçalho de tamanho seria: 1 (opcode) + 32 (floats) = 33 bytes (\x21 em hex)
    # Vamos testar o tamanho total do payload como 33 bytes (0x21 0x00 0x00 0x00)
    
    tamanho_payload = len(payload_floats) + 1  # 32 + 1 = 33 bytes
    cabecalho_tamanho = struct.pack('<I', tamanho_payload)
    opcode_resposta = b'\x62' # Mantém o 'b' ou o opcode correspondente de resposta
    
    pacote = cabecalho_tamanho + opcode_resposta + payload_floats
    return pacote

def iniciar_servidor():
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servidor.bind((HOST, PORT))
    servidor.listen(5)

    print("=" * 78)
    print(f"Servidor de Teste de Voltagens (8 Canais) rodando em {HOST}:{PORT}")
    print("=" * 78)

    while True:
        conexao_cliente, endereco_cliente = servidor.accept()
        print(f"\n[+] Cliente conectado: {endereco_cliente}")
        conexao_cliente.settimeout(15.0)

        contador_ciclos = 0

        try:
            with conexao_cliente:
                while True:
                    dados = conexao_cliente.recv(4096)
                    if not dados:
                        print("[-] Cliente desconectou.")
                        break

                    # Verifica se é a fase de handshake inicial (pacotes de 5 bytes)
                    if len(dados) == 5 and dados[4] != 0x62:
                        print(f"[{agora()}] Handshake recebido ({len(dados)} bytes). Ecoando resposta.")
                        conexao_cliente.sendall(dados)
                    
                    else:
                        # Entrou na fase de polling/loop principal (pacote com 'b' / 13 bytes)
                        contador_ciclos += 1
                        
                        # Gera as 8 voltagens dinâmicas
                        resposta_customizada = montar_pacote_voltagens(contador_ciclos)
                        
                        print(f"[{agora()}] Requisição de dados #{contador_ciclos} recebida. Enviando 8 voltagens simuladas... (Tam: {len(resposta_customizada)})")
                        
                        # Envia os dados customizados em vez de apenas dar echo
                        conexao_cliente.sendall(resposta_customizada)
                        
                        # Pequeno atraso para simular a taxa de atualização real do hardware (ex: ~2 atualizações por segundo)
                        time.sleep(0.5)

        except socket.timeout:
            print("[!] Timeout na conexão com o cliente.")
        except ConnectionResetError:
            print("[!] Conexão resetada pelo cliente.")
        except Exception as e:
            print(f"[!] Erro inesperado: {type(e).__name__}: {e}")
        
        print("[+] Conexão encerrada com este cliente. Aguardando nova conexão...\n")

if __name__ == "__main__":
    iniciar_servidor()