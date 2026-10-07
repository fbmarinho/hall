import socket
import struct
import time

HOST = '10.165.31.99'
PORT = 52106

def monitorizar_8_posicoes():
    print(f"A ligar ao servidor comercial em {HOST}:{PORT}...")
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        print("Ligação estabelecida! A executar handshake...\n")
        
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
            print("--- Monitor de 8 Posições / Canais Ativo ---")
            # Cabeçalho formatado para as 8 posições (Bytes 1 a 8)
            cabecalho = " | ".join([f"P{i}" for i in range(1, 9)])
            print(f"TEMPO    | {cabecalho}")
            print("-" * 55)
            
            while True:
                s.sendall(payload_continuo)
                resposta = s.recv(13)
                if not resposta:
                    print("O servidor fechou a ligação.")
                    break
                
                if len(resposta) >= 9:
                    timestamp = time.strftime('%H:%M:%S', time.localtime())
                    
                    # Extrair os 8 bytes individuais (posições 1 a 8) como inteiros com sinal (-128 a 127)
                    valores = [struct.unpack('b', bytes([resposta[i]]))[0] for i in range(1, 9)]
                    
                    val_str = " | ".join([f"{v:4d}" for v in valores])
                    print(f"{timestamp} | {val_str}")
                
                time.sleep(0.3)
                
        except KeyboardInterrupt:
            print("\nMonitorização encerrada.")

if __name__ == '__main__':
    monitorizar_8_posicoes()