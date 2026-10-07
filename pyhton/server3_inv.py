import socket
import struct
import time
from datetime import datetime

HOST = '0.0.0.0'
PORT = 52106  # NPDET
TIMEOUT_CLIENTE = 10.0

ARQUIVO_LOG = "protocolo3_52106.log"
ARQUIVO_BIN = "protocolo3_52106.bin"


def agora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def hex_dump(data):
    return " ".join(f"{b:02X}" for b in data)


def ascii_dump(data):
    return "".join(chr(b) if 32 <= b <= 126 else "." for b in data)


def u32_le(data):
    if len(data) < 4:
        return None
    return struct.unpack("<I", data[:4])[0]


def i32_le(data):
    if len(data) < 4:
        return None
    return struct.unpack("<i", data[:4])[0]


def f32_le(data):
    if len(data) < 4:
        return None
    return struct.unpack("<f", data[:4])[0]


def analisar(data):
    linhas = []
    linhas.append(f"HEX   : {hex_dump(data)}")
    linhas.append(f"ASCII : {ascii_dump(data)}")

    if len(data) >= 4:
        linhas.append(
            f"U32LE : {u32_le(data)}    "
            f"I32LE : {i32_le(data)}    "
            f"F32LE : {f32_le(data):.9g}"
        )

    if len(data) == 5:
        linhas.append(
            f"[5 bytes] campo0 U32LE={u32_le(data[:4])}, "
            f"campo1 U8={data[4]}"
        )

    if len(data) == 13:
        a = data[0:4]
        b = data[4:5]
        c = data[5:9]
        d = data[9:13]

        linhas.append("[13 bytes - divisão candidata 4+1+4+4]")
        linhas.append(f"  [00..03] U32LE={struct.unpack('<I', a)[0]}")
        linhas.append(f"  [04]     U8={b[0]}")
        linhas.append(
            f"  [05..08] U32LE={struct.unpack('<I', c)[0]} "
            f"I32LE={struct.unpack('<i', c)[0]} "
            f"F32LE={struct.unpack('<f', c)[0]:.9g}"
        )
        linhas.append(
            f"  [09..12] U32LE={struct.unpack('<I', d)[0]} "
            f"I32LE={struct.unpack('<i', d)[0]} "
            f"F32LE={struct.unpack('<f', d)[0]:.9g}"
        )

    return linhas


def registrar(arquivo_texto, direcao, seq, data):
    timestamp = agora()
    bloco = []
    bloco.append("")
    bloco.append("=" * 78)
    bloco.append(f"[{timestamp}] {direcao}  SEQ={seq}  LEN={len(data)}")
    bloco.extend(analisar(data))

    texto = "\n".join(bloco)
    print(texto)

    arquivo_texto.write(texto + "\n")
    arquivo_texto.flush()

    with open(ARQUIVO_BIN, "ab") as f:
        f.write(data)


servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
servidor.bind((HOST, PORT))
servidor.listen(5)

print("=" * 78)
print(f"Servidor TCP de investigação (Com Delay e Injeção Refinada)")
print(f"Escutando em {HOST}:{PORT}")
print("=" * 78)

with open(ARQUIVO_LOG, "a", encoding="utf-8") as log:
    while True:
        conexao_cliente = None

        try:
            conexao_cliente, endereco_cliente = servidor.accept()
            print(f"\n[+] Cliente conectado: {endereco_cliente}")

            log.write(
                f"\n\n{'#' * 78}\n"
                f"[{agora()}] NOVA CONEXÃO: {endereco_cliente}\n"
                f"{'#' * 78}\n"
            )
            log.flush()

            conexao_cliente.settimeout(TIMEOUT_CLIENTE)
            seq = 0

            with conexao_cliente:
                while True:
                    dados = conexao_cliente.recv(4096)

                    if not dados:
                        print("[-] O cliente encerrou a conexão.")
                        log.write(f"[{agora()}] CLIENTE DESCONECTOU\n")
                        log.flush()
                        break

                    seq += 1
                    registrar(log, "CLIENTE -> SERVIDOR", seq, dados)

                    # Simula o tempo de processamento do hardware antigo (~100ms)
                    time.sleep(0.1)

                    # Lógica de Resposta
                    if seq == 1:
                        resposta = dados
                    elif seq == 2:
                        resposta = dados
                    else:
                        # Se o cliente enviar blocos grandes (como o de 961 bytes), 
                        # podemos responder com eco ou com uma estrutura maior se necessário.
                        # Por enquanto, se o pacote recebido for grande, ecoamos; se for o de 13 bytes, injetamos.
                        if len(dados) == 13:
                            voltagem_canal_1 = 3.3
                            voltagem_canal_2 = 5.0
                            payload_canais = struct.pack('<ff', voltagem_canal_1, voltagem_canal_2)
                            resposta = dados[:5] + payload_canais
                        else:
                            resposta = dados

                    conexao_cliente.sendall(resposta)
                    registrar(log, "SERVIDOR -> CLIENTE", seq, resposta)

        except socket.timeout:
            print("[!] Timeout: nenhum dado recebido dentro do período.")
            log.write(f"[{agora()}] TIMEOUT\n")
            log.flush()

        except ConnectionResetError:
            print("[!] O cliente resetou a conexão.")
            log.write(f"[{agora()}] CONNECTION RESET\n")
            log.flush()

        except Exception as e:
            print(f"[!] Erro: {type(e).__name__}: {e}")
            log.write(f"[{agora()}] ERRO: {type(e).__name__}: {e}\n")
            log.flush()

        finally:
            if conexao_cliente is not None:
                try:
                    conexao_cliente.close()
                except Exception:
                    pass
            print("[+] Conexão encerrada.")