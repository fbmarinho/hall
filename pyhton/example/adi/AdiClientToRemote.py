import socket
import struct
import getpass

HOST = '127.0.0.1'
PORT = 23052


def teste_conexao_oficial():
    try:
        
        print(f"[*] Conectando à porta principal {HOST}:{PORT}...")
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(5.0)
        client.connect((HOST, PORT))
        print(f"[+] Conectado com sucesso na porta {PORT}!\n")
        
        # 2. Envia o comando
        # Conforme o AdiCommands.py, o Header tem 16 bytes: [Cmd (0x1002)][Param (0)][Length (0)][Format (0)]
        print("[>] Enviando comando...")
        command = 0x1002
        param = 0
        length = 0
        format = 0
        handshake_packet = struct.pack('<IIII', command, param, length, format)
        
        client.sendall(handshake_packet)
        
        resp = client.recv(16)
        if len(resp) == 16:
            cmd_r, param_r, val_r, len_r = struct.unpack('<IIII', resp)
            print(f"[<] Handshake respondido! Valor retornado: 0x{val_r:02X} (Decimal: {val_r})")
            
            if val_r == 0x0b:
                print("[+] Handshake validado com sucesso pelo servidor!")
            else:
                print("[!] O servidor respondeu, mas o valor de sucesso difere de 0x0b.")
        else:
            print("[-] Resposta do Handshake inválida ou incompleta.")
            return

        # 3. Envia o comando de Identification (0x101f)
        # O AdiClientToRemote envia metadados do cliente logo após o handshake
        exec_name = b"TestClient.py"
        host_name = socket.gethostname().encode('utf-8')
        try:
            user_name = getpass.getuser().encode('utf-8')
        except:
            user_name = b"tmapp"

        # Montagem do payload de Identificação conforme mapeado no AdiCommands.py
        # Estrutura típica: Inteiro (ID/Parâmetro) + Strings dinâmicas prefixadas por tamanho
        payload = struct.pack('<I', 1) # ID do cliente ou flag
        payload += struct.pack(f'<I{len(exec_name)}s', len(exec_name), exec_name)
        payload += struct.pack(f'<I{len(host_name)}s', len(host_name), host_name)
        payload += struct.pack(f'<I{len(user_name)}s', len(user_name), user_name)

        header_ident = struct.pack('<IIII', 0x101f, 0, len(payload), 0)
        
        print("\n[>] Enviando CMD_IDENTIFICATION (0x101f)...")
        client.sendall(header_ident + payload)
        
        resp_ident = client.recv(16)
        if len(resp_ident) >= 16:
            cmd_i, param_i, val_i, len_i = struct.unpack('<IIII', resp_ident[:16])
            print(f"[<] Identificação aceita! Resposta: Cmd=0x{cmd_i:04X}, Status/Val=0x{val_i:02X}")
        else:
            print("[-] Falha ao receber confirmação de identificação.")

    except Exception as e:
        print(f"\n[-] Erro durante a comunicação: {e}")
    finally:
        client.close()
        print("\n[*] Conexão encerrada.")

if __name__ == '__main__':
    teste_conexao_oficial()