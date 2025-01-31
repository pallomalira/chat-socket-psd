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

    def listarusuarios(self, conexao, nome):
        lista_usuarios = "Usuários conectados: " + ", ".join(self.clientes.keys())
        conexao.send(lista_usuarios.encode(FORMATO))
        
        
    def criar_grupo(self, arg, conexao):
        if arg:
            with self.lock:
                if arg not in self.grupos:
                    self.grupos[arg] = {}
                    conexao.send(f'Grupo "{arg}" criado!'.encode(FORMATO))
                else:
                    conexao.send("Erro, grupo já existente".encode(FORMATO))
        else:
            conexao.send("Erro, nome do grupo não pode ser vazio.".encode(FORMATO))
            
    def listar_grupos(self, conexao):
        if self.grupos:
            conexao.send(f'Grupos cadastrados: {", ".join(self.grupos.keys())}'.encode(FORMATO))
        else:
            conexao.send("Erro, nenhum grupo cadastrado".encode(FORMATO))
            
    
    def listar_usuarios_grupo(self, arg, conexao):
        if arg and arg in self.grupos:
            membros = ", ".join(self.grupos[arg].keys())
            conexao.send(f'Membros do grupo {arg}: {membros}'.encode(FORMATO))
        else:
            conexao.send("Erro, grupo não cadastrado".encode(FORMATO))

    def entrar_grupo(self, arg, nome, conexao):
        if arg and arg in self.grupos:
            with self.lock:
                self.grupos[arg][nome] = Cliente(nome, conexao)
            conexao.send(f'Você entrou no grupo {arg}.'.encode(FORMATO))
        else:
            conexao.send("Erro, grupo não existe".encode(FORMATO))

            
    def sair_grupo(self, arg, nome, conexao):
        if arg and arg in self.grupos and nome in self.grupos[arg]:
            with self.lock:
                self.grupos[arg].pop(nome, None)
            conexao.send(f'Você saiu do grupo {arg}.'.encode(FORMATO))
        else:
            conexao.send("Erro, grupo não existe ou você não está nele.".encode(FORMATO))

    def verificar_novo_cliente(self, novo_cliente):
        for cliente in self.clientes.values():
            if cliente.nome == novo_cliente.nome and cliente.is_online:
                return True
        return False
    
    def enviar_mensagens_pendentes(self, destinatario, mensagem):
    
        with self.lock:
            if destinatario not in self.mensagens_pendentes:
                self.mensagens_pendentes[destinatario] = []
                self.mensagens_pendentes[destinatario].append(mensagem)
                print(f"[MENSAGEM PENDENTE] Mensagem para {destinatario} armazenada.")


    def processar_comando(self, comando, nome, conexao):
        if comando.startswith("-msg "):
            partes = comando.split(" ", 3)
            if len(partes) < 4:
               conexao.send("[ERRO] Comando inválido. Formato correto: -msg U ou G NICK/GRUPO MENSAGEM".encode(FORMATO))
               return

            tipo, destinatarios, mensagem = partes[1], partes[2], partes[3]
            destinatarios = destinatarios.strip("[]").split(",")

            if tipo == "U": 
                for destinatario in destinatarios:
                    mensagem_formatada = self.formatar_mensagem(nome, "", mensagem)
                    if destinatario in self.clientes:
                        self.enviar_mensagem(nome, destinatario, mensagem_formatada)
                    else:
                        self.enviar_mensagens_pendentes(destinatario, mensagem_formatada)

            elif tipo == "G": 
                if destinatarios[0] in self.grupos:
                    for membro in self.grupos[destinatario[0]]:
                        mensagem_formatada = self.formatar_mensagem(nome, destinatarios[0], mensagem)
                        
                        if membro in self.clientes:
                            self.enviar_mensagem(nome, membro, mensagem_formatada)
                        else:
                            self.enviar_mensagens_pendentes(membro, mensagem_formatada)
                else:
                    conexao.send("[ERRO] Grupo não encontrado.".encode(FORMATO))

            else:
                conexao.send("[ERRO] Tipo inválido. Use 'U' para usuário ou 'G' para grupo.".encode(FORMATO))
                
                
        partes = comando.split(" ", 1)
        cmd = partes[0]
        args = partes[1] if len(partes) > 1 else ""

        if cmd == "-listarusuarios":
            self.listar_usuarios(conexao)
        elif cmd == "-criargrupo":
            self.criar_grupo(conexao, args)
        elif cmd == "-listargrupos":
            self.listar_grupos(conexao)
        elif cmd == "-listausrgrupo":
            self.listar_usuarios_grupo(conexao, args)
        elif cmd == "-entrargrupo":
            self.entrar_grupo(conexao, nome, args)
        elif cmd == "-sairgrupo":
            self.sair_grupo(conexao, nome, args)
        

    def tratar_cliente(self, conexao, endereco):
        try:
            while True:
                nome = conexao.recv(1024).decode(FORMATO)
                if nome in self.clientes:
                    conexao.send("[ERRO] Nome já em uso, escolha outro: ".encode(FORMATO))
                else:
                    conexao.send("[SUCESSO] Você está conectado!".encode(FORMATO))
                    break
            
            self.clientes[nome] = conexao
            print(f"[NOVA CONEXÃO] {nome} conectado do {endereco}")
            
            if nome in self.mensagens_pendentes:
                for mensagem in self.mensagens_pendentes.pop(nome):
                    conexao.send(mensagem.encode(FORMATO))
                print(f"[SERVIDOR] Mensagens entregues para {nome}")
            
            while True:
                comando = conexao.recv(1024).decode(FORMATO)
                if comando == "-sair":
                    print(f"[SERVIDOR] {nome} saiu do chat.")
                    break
                self.processar_comando(comando, nome, conexao)

                
        except Exception as e:
            print(f"[ERRO] {nome} desconectado inesperadamente: {e}")
        finally:
            if nome in self.clientes:
                self.clientes.pop(nome)
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