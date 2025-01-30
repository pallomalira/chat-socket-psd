import socket
import multiprocessing
import os
import traceback
from model import User

IP_SERVIDOR = "127.0.0.1"
PORTA = 5050
ENDERECO = (IP_SERVIDOR, PORTA)
FORMATO = 'utf-8'


class Server:

    clientes = None

    def __init__(self):
        self.iniciar_servidor()

    def notificar_entrada(self, nome, clientes):
        for outro_nome, outro_cliente in clientes.items():
            if outro_nome != nome:
                try:
                    outro_cliente.send(f"[SERVIDOR] {nome} entrou no chat.".encode(FORMATO))
                    print(f"[SERVIDOR] Notificação enviada para {outro_nome}: {nome} entrou no chat.")
                except Exception as e:
                    print(f"[ERRO] Não foi possível notificar {outro_nome}: {e}")
                    outro_cliente.close()
                    clientes.pop(outro_nome, None)

    def enviar_mensagem(self, mensagem, nome_remetente, clientes):
        for nome, cliente in clientes.items():
            if nome != nome_remetente:
                try:
                    cliente.send(mensagem)
                    print(f"[SERVIDOR] Mensagem de {nome_remetente} enviada para {nome}: {mensagem.decode(FORMATO)}")
                except Exception as e:
                    print(f"[ERRO] Não foi possível enviar a mensagem para {nome}: {e}")
                    cliente.close()
                    clientes.pop(nome, None)

    def tratar_cliente(self, conexao, endereco):

        is_cadastrado = False
        print(self.clientes)
        print(self.clientes)
        try:
            nome = conexao.recv(1024).decode(FORMATO)
            self.clientes[nome] = conexao
            print(self.clientes)
            print(f"[NOVA CONEXÃO] {nome} conectado de {endereco}")

            self.notificar_entrada(nome, self.clientes)
            # with multiprocessing.Manager() as gerenciador:
            #     grupos['ok'] = gerenciador.list()
            while True:
                mensagem = conexao.recv(1024).decode(FORMATO)
                if not mensagem:
                    break

                if mensagem.strip() == "/listar":
                    lista_usuarios = "Usuários conectados: " + ", ".join(self.clientes.keys())
                    conexao.send(lista_usuarios.encode(FORMATO))
                    print(f"[SERVIDOR] Lista enviada para {nome}: {lista_usuarios}")
                elif mensagem == "/sair":
                    print(f"[SERVIDOR] {nome} solicitou sair.")
                    break
                elif not mensagem:
                    raise Exception()
                #group context
                elif mensagem.strip().split()[0] == "-criargrupo":
                    nome_grupo = mensagem.split()[1]
                    print(self.grupos)
                    if nome_grupo not in self.grupos.keys():
                        with multiprocessing.Manager().Lock():
                            self.grupos[nome_grupo] = {}
                        print(self.grupos)
                        conexao.send(f'Grupo "{nome_grupo}" criado!'.encode(FORMATO))
                    elif not nome_grupo:
                        conexao.send("Não é possível criar um grupo com o nome vazio.".encode(FORMATO))
                    else:
                        conexao.send("Error, grupo já existente".encode(FORMATO))

                elif mensagem.strip() == "-listargrupos":
                    if not self.grupos:
                        conexao.send('Erro, nenhum grupo cadastrado'.encode(FORMATO))
                    else:
                        grupos_existentes = ", ".join(self.grupos.keys())
                        conexao.send(f'Grupos cadastrados: {grupos_existentes}'.encode(FORMATO))

                elif mensagem.strip().split()[0] == "-entrargrupo":
                    nome_grupo = mensagem.split()[1]
                    if nome_grupo not in self.grupos.keys():
                        conexao.send('Erro, grupo não existe'.encode(FORMATO))
                    else:

                        with multiprocessing.Manager().Lock():
                            self.grupos[nome_grupo][nome] = User(nome, conexao)
                        print(self.grupos)
                        
                        conexao.send(f'Você entrou no grupo {nome_grupo}.'.encode(FORMATO))

                elif mensagem.strip().split()[0] == "-sairgrupo":
                    nome_grupo = mensagem.split()[1]
                    if nome_grupo not in self.grupos.keys():
                        conexao.send('Erro, grupo não existe'.encode(FORMATO))
                    else:
                        self.grupos[nome_grupo].pop(nome, None)           
                        print(self.grupos)

                else:
                    self.enviar_mensagem(f"{nome}: {mensagem}".encode(FORMATO), nome_remetente=nome, clientes=self.clientes)

        except Exception as e:
            traceback.print_exc(e)
            print(f"[ERRO] {nome} desconectado inesperadamente: {e}")
        finally:
            if not is_cadastrado:
                print(f"[DESCONECTADO] {nome} saiu do chat.")

                for outro_nome, outro_cliente in self.clientes.items():
                    if outro_nome != nome:
                        outro_cliente.send(f"[SERVIDOR] {nome} saiu do chat.".encode(FORMATO))

                conexao.close()
                self.clientes.pop(nome, None)

    def iniciar_servidor(self):
        servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        servidor.bind(ENDERECO)
        servidor.listen()
        
        print(f"[SERVIDOR] Ouvindo em {IP_SERVIDOR}:{PORTA}")

        with multiprocessing.Manager() as gerenciador:
            self.clientes = gerenciador.dict()
            self.grupos = gerenciador.dict()
            self.mensagens_pendentes = gerenciador.list()
           
        while True:
            conexao, endereco = servidor.accept()
            processo = multiprocessing.Process(target=self.tratar_cliente, args=(conexao, endereco))
            processo.start()
            
            print(f"[CONEXÃO ACEITA] Conexão ativa com {endereco}")

if __name__ == "__main__":
    Server()
