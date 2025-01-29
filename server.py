import socket
import multiprocessing

IP_SERVIDOR = "127.0.0.1"
PORTA = 5050
ENDERECO = (IP_SERVIDOR, PORTA)
FORMATO = 'utf-8'

def notificar_entrada(nome, clientes):
    for outro_nome, outro_cliente in clientes.items():
        if outro_nome != nome:
            try:
                outro_cliente.send(f"[SERVIDOR] {nome} entrou no chat.".encode(FORMATO))
                print(f"[SERVIDOR] Notificação enviada para {outro_nome}: {nome} entrou no chat.")
            except Exception as e:
                print(f"[ERRO] Não foi possível notificar {outro_nome}: {e}")
                outro_cliente.close()
                clientes.pop(outro_nome, None)

def enviar_mensagem(mensagem, nome_remetente, clientes):
    for nome, cliente in clientes.items():
        if nome != nome_remetente:
            try:
                cliente.send(mensagem)
                print(f"[SERVIDOR] Mensagem de {nome_remetente} enviada para {nome}: {mensagem.decode(FORMATO)}")
            except Exception as e:
                print(f"[ERRO] Não foi possível enviar a mensagem para {nome}: {e}")
                cliente.close()
                clientes.pop(nome, None)

def tratar_cliente(conexao, endereco, clientes):
    try:
        nome = conexao.recv(1024).decode(FORMATO)
        clientes[nome] = conexao
        print(f"[NOVA CONEXÃO] {nome} conectado de {endereco}")

        notificar_entrada(nome, clientes)

        while True:
            mensagem = conexao.recv(1024).decode(FORMATO)
            if not mensagem:
                break

            if mensagem == "/listar":
                lista_usuarios = "Usuários conectados: " + ", ".join(clientes.keys())
                conexao.send(lista_usuarios.encode(FORMATO))
                print(f"[SERVIDOR] Lista enviada para {nome}: {lista_usuarios}")
            elif mensagem == "/sair":
                print(f"[SERVIDOR] {nome} solicitou sair.")
                break
            else:
                enviar_mensagem(f"{nome}: {mensagem}".encode(FORMATO), nome_remetente=nome, clientes=clientes)
    except Exception as e:
        print(f"[ERRO] {nome} desconectado inesperadamente: {e}")
    finally:
        print(f"[DESCONECTADO] {nome} saiu do chat.")

        for outro_nome, outro_cliente in clientes.items():
            if outro_nome != nome:
                outro_cliente.send(f"[SERVIDOR] {nome} saiu do chat.".encode(FORMATO))

        conexao.close()
        clientes.pop(nome, None)

def iniciar_servidor():
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servidor.bind(ENDERECO)
    servidor.listen()
    print(f"[SERVIDOR] Ouvindo em {IP_SERVIDOR}:{PORTA}")

    with multiprocessing.Manager() as gerenciador:
        clientes = gerenciador.dict()
        while True:
            conexao, endereco = servidor.accept()
            processo = multiprocessing.Process(target=tratar_cliente, args=(conexao, endereco, clientes))
            processo.start()
            print(f"[CONEXÃO ACEITA] Conexão ativa com {endereco}")

if __name__ == "__main__":
    iniciar_servidor()