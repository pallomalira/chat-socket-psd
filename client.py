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
        except:
            print("[ERRO] Conexão perdida.")
            cliente.close()
            break

def iniciar_cliente():
    cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    cliente.connect(ENDERECO)

    nome = input("Digite seu nome: ")
    cliente.send(nome.encode(FORMATO))  

    # Inicia uma thread para receber mensagens sem bloquear o envio de outras
    thread = threading.Thread(target=receber_mensagens, args=(cliente,))
    thread.daemon = True  # Torna a thread de recebimento uma thread daemon
    thread.start()

    while True:
        try:
            mensagem = input()
            if mensagem.lower() == "-sair":
                cliente.send("-sair".encode(FORMATO))
                print("[DESCONECTADO] Saindo do chat...")
                cliente.close()
                break
            else:
                cliente.send(mensagem.encode(FORMATO))
        except KeyboardInterrupt:
            cliente.send("-sair".encode(FORMATO))
            print("[DESCONECTADO] Saindo do chat...")
            cliente.close()
            break

if __name__ == "__main__":
    iniciar_cliente()
