import socket
import struct
import time
from datetime import datetime

HOST = '10.165.31.99'
PORT = 52106
ARQUIVO_LOG = 'respostas_servidor.csv'

def decifrar_e_gravar(dados, arquivo_log):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    bytes_hex = dados.hex()
    
    # Valores padrão caso a desestruturação falhe
    b_int = None
    b_float = None
    b_float_2 = None
    
    if len(dados) >= 8:
        try:
            b_int = struct.unpack('<i', dados[4:8])[0]
            b_float = struct.unpack('<f', dados[4:8])[0]
            if len(dados) >= 12:
                b_float_2 = struct.unpack('<f', dados[8:12])[0]
        except Exception:
            pass

    # Imprimir no terminal
    print(f"[{timestamp}] Bytes: {bytes_hex} | Int: {b_int} | Float1: {b_float} | Float2: {b_float_2}")
    
    # Gravar no arquivo CSV (Timestamp, Hex, Int, Float1, Float2)
    with open(arquivo_log, 'a', encoding='utf-8') as f:
        f.write(f"{timestamp},{bytes_hex},{b_int},{b_float},{b_float_2}\n")

def iniciar_cliente():
    print(f"A ligar ao servidor comercial em {HOST}:{PORT}...")
    
    # Criar ou limpar o cabeçalho do arquivo de log
    with open(ARQUIVO_LOG, 'w', encoding='utf-8') as f:
        f.write("Timestamp,Bytes_Hex,Int_Bytes_4_8,Float_Bytes_4_8,Float_Bytes_8_12\n")
    
    print(f"Arquivo de log criado: {ARQUIVO_LOG}\n")
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        print("Ligação estabelecida com sucesso!\n")
        
        sequencia_mensagens = [
            b'\x01\x00\x00\x00`',
            b'\x01\x00\x00\x00f',
            b'\x01\x00\x00\x00^',
            b'\x01\x00\x00\x00d',
            b'\x01\x00\x00\x00h',
            b'\t\x00\x00\x00b\xff\xff\xff\xff7P\xdd\x08',
            b'\t\x00\x00\x00b\x00\x00\x00\x007P\xdd\x08'
        ]
        
        try:
            for msg in sequencia_mensagens:
                s.sendall(msg)
                resposta = s.recv(len(msg))
                time.sleep(0.2)
            
            payload_continuo = b'\t\x00\x00\x00b\x00\x00\x00\x007P\xdd\x08'
            
            print("A entrar em ciclo de recolha. Altere a voltagem no equipamento e verifique o arquivo de log.")
            while True:
                s.sendall(payload_continuo)
                resposta = s.recv(13)
                if not resposta:
                    print("O servidor fechou a ligação.")
                    break
                
                decifrar_e_gravar(resposta, ARQUIVO_LOG)
                time.sleep(0.5)
                
        except KeyboardInterrupt:
            print(f"\nCliente interrompido. Dados salvos em {ARQUIVO_LOG}.")

if __name__ == '__main__':
    iniciar_cliente()