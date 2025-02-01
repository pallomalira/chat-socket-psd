import socket
import threading

PORTA = 5050
FORMATO = 'utf-8'
SERVIDOR = "127.0.0.1"
ENDERECO = (SERVIDOR, PORTA)

def receber_mensagens(cliente):
    while True:
        try:
            mensagem = cliente.recv(1024).decode(FORMATO)
            if not mensagem:
                break
            print(mensagem)
        except Exception:
            print("[ERRO] Conexão perdida.")
            cliente.close()
            break

def iniciar_cliente():
    conexao = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    conexao.connect(ENDERECO)

    nome = input("Digite seu nome: ")
    conexao.send(nome.encode(FORMATO))  

    # Inicia uma thread para receber mensagens sem bloquear o envio de outras
    thread = threading.Thread(target=receber_mensagens, args=(conexao,))
    thread.daemon = True  # Torna a thread de recebimento uma thread daemon
    thread.start()

    while True:
        try:
            mensagem = input()
            if mensagem.lower() == "-sair":
                conexao.send("-sair".encode(FORMATO))
                print("[DESCONECTADO] Saindo do chat...")
                conexao.close()
                break
            else:
                conexao.send(mensagem.encode(FORMATO))
        except KeyboardInterrupt:
            conexao.send("-sair".encode(FORMATO))
            print("[DESCONECTADO] Saindo do chat...")
            conexao.close()
            break

if __name__ == "__main__":
    iniciar_cliente()
