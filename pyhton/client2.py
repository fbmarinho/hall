import socket
import struct
from pathlib import Path

HOST = "127.0.0.1"
PORT = 23052

VERSOES = [
    0x1002,
    0x1003,
    0x1004
]

Path("capturas").mkdir(exist_ok=True)

for versao in VERSOES:

    mensagem = struct.pack(
        "<IIII",
        101,
        versao,
        1,
        0
    )

    print(
        f"\nTestando versão "
        f"0x{versao:04X} ({versao})"
    )

    resposta = b""

    try:

        with socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM
        ) as sock:

            sock.settimeout(3)

            sock.connect((HOST, PORT))

            sock.sendall(mensagem)

            while True:

                try:

                    dados = sock.recv(4096)

                    if not dados:
                        break

                    resposta += dados

                except socket.timeout:
                    break

                except ConnectionResetError:
                    break

    except Exception as e:

        print("Erro:", e)
        continue

    nome = f"capturas/resposta_{versao:04X}.bin"

    Path(nome).write_bytes(resposta)

    print(f"Recebidos: {len(resposta)} bytes")
    print(f"Arquivo: {nome}")

    if len(resposta) >= 16:

        opcode, campo1, campo2, tamanho = struct.unpack(
            "<IIII",
            resposta[:16]
        )

        print(f"Opcode   : {opcode}")
        print(f"Campo 1  : {campo1}")
        print(f"Campo 2  : {campo2}")
        print(f"Tamanho  : {tamanho}")

        print(
            "Framing OK:",
            len(resposta) == 16 + tamanho
        )