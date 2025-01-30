import socket
import threading
import os 

PORTA = 5050
FORMATO = 'utf-8'
SERVIDOR = "127.0.0.1"
ENDERECO = (SERVIDOR, PORTA)

def receber_mensagens(cliente):
    while True:
        try:
            mensagem = cliente.recv(1024).decode(FORMATO)
            if not mensagem:
                os._exit(0) # então finalizo o processso (somente) desse cliente
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

    thread = threading.Thread(target=receber_mensagens, args=(cliente,))
    thread.start()

    while True:
        mensagem = input()
        if mensagem.lower() == "/sair":
            cliente.send("/sair".encode(FORMATO))
            print("[DESCONECTADO] Saindo do chat...")
            cliente.close()
            break
        cliente.send(mensagem.encode(FORMATO))

if __name__ == "__main__":
    iniciar_cliente()
