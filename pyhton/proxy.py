import datetime
import socket
import struct
import threading

SERVER_ADDR = ('127.0.0.1', 23052)
PROXY_PORT = 55000


def hex_dump(data: bytes, direction: str):
    timestamp = datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]
    hex_bytes = ' '.join(f'{b:02X}' for b in data)
    ascii_bytes = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in data)

    print(f'\n[{timestamp}] === {direction} ({len(data)} bytes) ===')
    print(f'HEX  : {hex_bytes}')
    print(f'ASCII: {ascii_bytes}')

    # Tenta decodificar o cabeçalho padrão de 16 bytes se houver tamanho suficiente
    if len(data) >= 16:
        try:
            op, status, extra1, extra2 = struct.unpack('<IIII', data[:16])
            print(
                f'HEADER DECODIFICADO -> Opcode: {op} | Status: {status} | Extra1: 0x{extra1:08X} | Extra2: 0x{extra2:08X}'
            )
            if len(data) > 16:
                print(f'PAYLOAD ADICIONAL  -> {len(data) - 16} bytes de corpo.')
        except Exception:
            pass


def bridge(source_sock, target_sock, direction_label):
    packet_count = 0
    while True:
        try:
            data = source_sock.recv(4096)
            if not data:
                break
            packet_count += 1
            hex_dump(data, f'{direction_label} [Pacote #{packet_count}]')
            target_sock.sendall(data)
        except Exception as e:
            print(f'Conexão encerrada ({direction_label}): {e}')
            break

    source_sock.close()
    target_sock.close()


def main():
    proxy = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    proxy.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    proxy.bind(('127.0.0.1', PROXY_PORT))
    proxy.listen(1)

    print(f'[*] Proxy escutando em 127.0.0.1:{PROXY_PORT}')
    print(f'[*] Redirecionando para servidor em {SERVER_ADDR[0]}:{SERVER_ADDR[1]}')
    print('[!] Altere a porta do seu CLIENTE comercial para 23053 para capturar.\n')

    while True:
        client_sock, addr = proxy.accept()
        print(f'[+] Cliente conectado de {addr}')

        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.connect(SERVER_ADDR)

        # Inicia threads bidirecionais
        t1 = threading.Thread(
            target=bridge, args=(client_sock, server_sock, 'CLIENTE -> SERVIDOR')
        )
        t2 = threading.Thread(
            target=bridge, args=(server_sock, client_sock, 'SERVIDOR -> CLIENTE')
        )

        t1.start()
        t2.start()


if __name__ == '__main__':
    main()