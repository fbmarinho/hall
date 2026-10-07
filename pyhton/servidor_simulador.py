import socket
import time

HOST = '0.0.0.0'
PORT = 52106

def iniciar_servidor_simulador():
    print(f"Servidor simulador robusto a iniciar na porta {PORT}...")
    print("Pressione [Ctrl+C] no teclado para encerrar o servidor a qualquer momento.\n")
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((HOST, PORT))
        server_socket.listen(1)
        
        try:
            while True:
                print("À espera de ligação do cliente...")
                conn, addr = server_socket.accept()
                print(f"Cliente conectado de {addr}")
                
                try:
                    # 1. Handshake exato (7 passos)
                    # Conhecemos os tamanhos exatos de cada mensagem enviada pelo cliente na sequência:
                    # Passos 1 a 5: 5 bytes cada (b'\x01\x00\x00\x00...')
                    # Passos 6 e 7: 16 bytes cada (b'\t\x00\x00\x00b...')
                    tamanhos_handshake = [5, 5, 5, 5, 5, 16, 16]
                    
                    sucesso_handshake = True
                    for i, tamanho_esperado in enumerate(tamanhos_handshake):
                        # Lê exatamente o tamanho do passo atual do handshake
                        dados = conn.recv(tamanho_esperado)
                        if not dados or len(dados) != tamanho_esperado:
                            print(f"[Handshake] Erro no passo {i+1}: esperado {tamanho_esperado} bytes, recebido {len(dados) if dados else 0}")
                            sucesso_handshake = False
                            break
                        
                        print(f"[Handshake] Passo {i+1} recebido e validado ({len(dados)} bytes): {dados.hex()}")
                        # Ecoa de volta exatamente os mesmos bytes
                        conn.sendall(dados)
                        time.sleep(0.05)
                    
                    if not sucesso_handshake:
                        conn.close()
                        continue
                    
                    print("\nHandshake concluído com sucesso! Entrando no modo contínuo...")
                    
                    # 2. Modo Contínuo (Request-Response rigoroso)
                    # O cliente envia o payload contínuo (16 bytes) e o servidor responde com o bloco de dados (13 bytes)
                    contador = 0
                    while True:
                        # Lê o pedido contínuo enviado pelo cliente (esperamos 16 bytes do pacote contínuo)
                        pedido = conn.recv(16)
                        if not pedido:
                            print("O cliente fechou a ligação.")
                            break
                        
                        # Gerar resposta de 13 bytes simulados
                        # Byte 0: Cabeçalho (b'\t')
                        # Bytes 1-12: Dados simulados (rampa cíclica para testarmos no cliente)
                        cabecalho = b'\t'
                        val_teste = contador % 256
                        
                        payload_simulado = bytes([
                            val_teste, val_teste, val_teste, val_teste,
                            100, 100, 100, 100,
                            50, 50, 50, 50
                        ])
                        
                        resposta = cabecalho + payload_simulado
                        conn.sendall(resposta)
                        
                        contador += 1
                        time.sleep(0.05)
                        
                except Exception as e:
                    print(f"Erro na conexão com o cliente: {e}")
                finally:
                    conn.close()
                    print("Conexão fechada com este cliente. À espera de nova ligação...\n")
                    
        except KeyboardInterrupt:
            print("\n\n[Servidor] Interrompido pelo utilizador com Ctrl+C no teclado. A encerrar com segurança.")

if __name__ == '__main__':
    iniciar_servidor_simulador()