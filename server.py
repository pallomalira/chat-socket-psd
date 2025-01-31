import socket
import multiprocessing
import os
import traceback
from multiprocessing.connection import Client
import datetime

from model import Cliente

IP_SERVIDOR = "127.0.0.1"
PORTA = 5050
ENDERECO = (IP_SERVIDOR, PORTA)
FORMATO = 'utf-8'


class Server:

    clientes = None
    grupos = None
    mensagens_pendentes = None

    def __init__(self):
        manager = multiprocessing.Manager()
        self.clientes = manager.dict()
        self.grupos = manager.dict()
        self.mensagens_pendentes = manager.dict()

        self.lock = multiprocessing.Lock()  # Lock para proteger o acesso a recursos compartilhados
        self.iniciar_servidor()

    def formatar_mensagem(self, nick, grupo, mensagem):
        hora_atual = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        if grupo:
            return f"({nick}, {grupo}, {hora_atual}) {mensagem}"
        return f"({nick}) {mensagem}"

    def enviar_mensagem(self, remetente, destinatario, mensagem):
        if destinatario in self.clientes:
            try:
                self.clientes[destinatario].send(mensagem.encode(FORMATO))
                print(f"[SERVIDOR] {remetente} enviou mensagem para {destinatario}: {mensagem}")
            except:
                print(f"[ERRO] Não foi possível enviar para {destinatario}")
                self.clientes.pop(destinatario, None)

    def listar(self, conexao, nome):
        lista_usuarios = "Usuários conectados: " + ", ".join(self.clientes.keys())
        conexao.socket.send(lista_usuarios.encode(FORMATO))
        print(f"[SERVIDOR] Lista enviada para {nome}: {lista_usuarios}")

    def sair(self, nome):
        if nome in self.clientes:
            del self.clientes[nome]

    def criar_grupo(self, conexao, mensagem):
        nome_grupo = mensagem.split()[1]
        with self.lock:
            if nome_grupo not in self.grupos.keys():
                self.grupos[nome_grupo] = {}
                conexao.socket.send(f'Grupo "{nome_grupo}" criado!'.encode(FORMATO))
            elif not nome_grupo:
                conexao.socket.send("Não é possível criar um grupo com o nome vazio.".encode(FORMATO))
            else:
                conexao.socket.send("Erro, grupo já existente".encode(FORMATO))

    def listar_grupos(self, conexao):
        if not self.grupos:
            conexao.socket.send('Erro, nenhum grupo cadastrado'.encode(FORMATO))
        else:
            grupos_existentes = ", ".join(self.grupos.keys())
            conexao.socket.send(f'Grupos cadastrados: {grupos_existentes}'.encode(FORMATO))

    def entrar_grupo(self, conexao, mensagem, nome):
        nome_grupo = mensagem.split()[1]
        if nome_grupo not in self.grupos.keys():
            conexao.socket.send('Erro, grupo não existe'.encode(FORMATO))
        else:
            with multiprocessing.Manager().Lock():
                self.grupos[nome_grupo][nome] = Cliente(nome, conexao)
            print(self.grupos)

            conexao.socket.send(f'Você entrou no grupo {nome_grupo}.'.encode(FORMATO))

    def sair_grupo(self, conexao, mensagem, nome):
        nome_grupo = mensagem.split()[1]
        if nome_grupo not in self.grupos.keys():
            conexao.socket.send('Erro, grupo não existe'.encode(FORMATO))
        else:
            self.grupos[nome_grupo].pop(nome, None)
            print(self.grupos)

    def verificar_novo_cliente(self, novo_cliente):
        for cliente in self.clientes.values():
            if cliente.nome == novo_cliente.nome and cliente.is_online:
                return True
        return False

    def processar_comando(self, comando, nome, cliente):
        if comando.startswith("-msg "):
            partes = comando.split(" ", 3)
            if len(partes) != 4:
                cliente.socket.send("[ERRO] Comando inválido. Formato correto: -msg U ou G NICK/GRUPO MENSAGEM".encode(FORMATO))
                return

            tipo, destinatarios, mensagem = partes[1], partes[2], partes[3]
            destinatarios = destinatarios.strip("[]").split(",")

            if tipo == "U": 
                for destinatario in destinatarios:
                    destinatario = destinatario.strip()
                    if destinatario in self.clientes:
                        mensagem_formatada = self.formatar_mensagem(nome, "", mensagem)
                        self.enviar_mensagem(remetente=nome, destinatario=destinatario, mensagem=mensagem_formatada)
                    else:
                        self.enviar_mensagens_pendentes(destinatario, mensagem)

            elif tipo == "G":  # Envio para grupo
                if destinatarios[0] in self.grupos:
                    grupo_nome = destinatarios[0]
                    for membro in self.grupos[grupo_nome]:
                        mensagem_formatada = self.formatar_mensagem(nome, grupo_nome, mensagem)
                        if membro in self.clientes:
                            self.enviar_mensagem(remetente=nome, destinatario=membro, mensagem=mensagem_formatada)
                        else:
                            self.enviar_mensagens_pendentes(membro, mensagem_formatada)
                else:
                    cliente.socket.send("[ERRO] Grupo não encontrado.".encode(FORMATO))

            else:
                cliente.socket.send("[ERRO] Tipo inválido. Use 'U' para usuário ou 'G' para grupo.".encode(FORMATO))

    def tratar_cliente(self, conexao, endereco):
        try:
            nome = conexao.recv(1024).decode(FORMATO)
            novo_cliente = Cliente(nome, conexao)
            if nome in self.clientes:
                conexao.socket.send("[ERRO] Nome já em uso, escolha outro.".encode(FORMATO))
                conexao.close()
                return

            print(f"[NOVA CONEXÃO] {nome} conectado de {endereco}")

            while True:
                
                try:
                    mensagem = conexao.recv(1024).decode(FORMATO)

                    if not mensagem:
                        break
                    print(f"[SERVIDOR] {nome} enviou uma mensagem para {conexao}:{mensagem}")

                    with self.lock:
                        self.mensagens_pendentes[endereco] = mensagem

                    mensagem = mensagem.strip()

                    if mensagem == "-listar":
                        self.listar(conexao, nome)

                    elif mensagem == "-sair":
                        self.sair(nome)
                        break

                    elif mensagem.startswith("-"):
                        comando = mensagem.split()[0]

                        if comando == "-criargrupo":
                            self.criar_grupo(conexao, mensagem)

                        elif comando == "-listargrupos":
                            self.listar_grupos(conexao)

                        elif comando == "-entrargrupo":
                            self.entrar_grupo(conexao, mensagem, nome)

                        elif comando == "-sairgrupo":
                            self.sair_grupo(conexao, mensagem, nome)

                        else:
                            self.processar_comando(mensagem, nome, novo_cliente)

                except Exception as e:
                    traceback.print_exc()
                    print(f"[ERRO] {nome} desconectado inesperadamente: {e}")
                    break

        except Exception as e:
            traceback.print_exc()
            print(f"[ERRO] {endereco} encontrou um erro: {e}")

        conexao.close()

    def iniciar_servidor(self):
        servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        servidor.bind(ENDERECO)
        servidor.listen()

        print(f"[SERVIDOR] Ouvindo em {ENDERECO}:")

        while True:
            conexao, endereco = servidor.accept()
            processo = multiprocessing.Process(target=self.tratar_cliente, args=(conexao, endereco))
            processo.start()
            print(f"[CONEXÃO ACEITA] Conexão ativa com {endereco}")


if __name__ == "__main__":
    Server()
