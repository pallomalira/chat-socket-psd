import socket
import multiprocessing
import os
import traceback
from multiprocessing.connection import Client
import datetime
import threading
from model import Cliente
import time

IP_SERVIDOR = "127.0.0.1"
PORTA = 5050
ENDERECO = (IP_SERVIDOR, PORTA)
FORMATO = 'utf-8'


class Server:

    clientes = {}
    grupos = {}
    mensagens_pendentes = {}

    def __init__(self):
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

    def listarusuarios(self, conexao):
        lista_usuarios = "Usuários conectados: " + ", ".join(self.clientes.keys())
        conexao.send(lista_usuarios.encode(FORMATO))
        
        
    def criar_grupo(self, conexao, nome, nome_grupo):
        if nome_grupo:
            
            if nome_grupo not in self.grupos:
                self.grupos[nome_grupo] = {nome: Cliente(nome, conexao)}
                conexao.send(f'Grupo "{nome_grupo}" criado e você foi adicionado!'.encode(FORMATO))
            else:
                conexao.send("Erro, grupo já existente.".encode(FORMATO))
        else:
            conexao.send("Erro, nome do grupo não pode ser vazio.".encode(FORMATO))

            
    def listar_grupos(self, conexao):
        if self.grupos:
            conexao.send(f'Grupos cadastrados: {", ".join(self.grupos.keys())}'.encode(FORMATO))
        else:
            conexao.send("Erro, nenhum grupo cadastrado".encode(FORMATO))
            
    
    def listar_usuarios_grupo(self, conexao, args):
        if args in self.grupos and isinstance(self.grupos[args], dict):
            membros = list(self.grupos[args].keys())
            if membros:
                membros_gp = ", ".join(membros)
                
                conexao.send(f'Membros do grupo {args}: {membros_gp}'.encode(FORMATO))
            else:
                conexao.send(f'O grupo {args} está vazio.'.encode(FORMATO))
                
        else:
            conexao.send("Erro, grupo não cadastrado".encode(FORMATO))

    def entrar_grupo(self, conexao, nome, args):
        if args in self.grupos:
            if not isinstance(self.grupos[args], dict):
                self.grupos[args] = {}
            self.grupos[args][nome] = nome
            conexao.send(f'Você entrou no grupo {args}.'.encode(FORMATO))
            
        else:
            conexao.send("Erro, grupo não existe".encode(FORMATO))

            
    def sair_grupo(self, conexao, nome, args):
        if args in self.grupos and isinstance(self.grupos[args], dict):
            
            if nome in self.grupos[args]:
                del self.grupos[args][nome]
                conexao.send(f'Você saiu do grupo {args}.'.encode(FORMATO))
            
            else:
                conexao.send("Erro, você não está nesse grupo.".encode(FORMATO))
                   
        else:
            conexao.send("Erro, grupo não existe.".encode(FORMATO))

                    
            
    def verificar_novo_cliente(self, novo_cliente):
        for cliente in self.clientes.values():
            if cliente.nome == novo_cliente.nome and cliente.is_online:
                return True
        return False
    
    


    def processar_comando(self, comando, nome, conexao):
        if comando.startswith("-msg "):
           
            partes = comando.split(" ", 3)
            print(partes)
            if len(partes) < 4:
               conexao.send("[ERRO] Comando inválido. Formato correto:\n -msg U NICK MENSAGEM ou \n -msg G GRUPO MENSAGEM".encode(FORMATO))
               return

            tipo, destinatarios, mensagem = partes[1], partes[2], partes[3]
            print(destinatarios)
            destinatarios = destinatarios.strip("[]").split(",")
            print(destinatarios)
            if tipo == "U": 
                for destinatario in destinatarios:
                    mensagem_formatada = self.formatar_mensagem(nome, "", mensagem)
                    if destinatario in self.clientes:
                        self.enviar_mensagem(nome, destinatario, mensagem_formatada)
                    else:
                        self.guardar_mensagens_pendentes(destinatario, mensagem_formatada)

            elif tipo == "G": 
                try:
                    if destinatarios[0] in self.grupos:
                        for membro in self.grupos[destinatarios[0]]:
                            mensagem_formatada = self.formatar_mensagem(nome, destinatarios[0], mensagem)
                            
                            if membro in self.clientes:
                                self.enviar_mensagem(nome, membro, mensagem_formatada)
                            else:
                                self.guardar_mensagens_pendentes(membro, mensagem_formatada)
                    else:
                        conexao.send("[ERRO] Grupo não encontrado.".encode(FORMATO))
                except Exception as e:
                    print(e)

            else:
                conexao.send("[ERRO] Tipo inválido. Use 'U' para usuário ou 'G' para grupo.".encode(FORMATO))
                
                
        partes = comando.split(" ", 1)
        cmd = partes[0]
        args = partes[1] if len(partes) > 1 else ""

        if cmd == "-listarusuarios":
            self.listarusuarios(conexao)
        elif cmd == "-criargrupo":
            self.criar_grupo(conexao, nome, args)
        elif cmd == "-listargrupos":
            self.listar_grupos(conexao)
        elif cmd == "-listausrgrupo":
            self.listar_usuarios_grupo(conexao,args)
        elif cmd == "-entrargrupo":
            self.entrar_grupo(conexao, nome, args)
        elif cmd == "-sairgrupo":
            self.sair_grupo(conexao, nome, args)

    def guardar_mensagens_pendentes(self, destinatario, mensagem):
        # criar um armazenamento de grupo e privado separados, pois o armazenamento em grupo deve ser enviado para todos os usuários do grupo que estiverem online e offline. Ou seja, enquando todos não receberem, não podemos excluir da base.
        if destinatario not in self.mensagens_pendentes:
            self.mensagens_pendentes[destinatario] = []
            self.mensagens_pendentes[destinatario].append(mensagem)
        else:
            self.mensagens_pendentes[destinatario].append(mensagem)

        print(f"[MENSAGEM PENDENTE] Mensagem para {destinatario} armazenada.")

    def enviar_mensagens_pendentes(self, nome, conexao):
        if nome in self.mensagens_pendentes:
            for mensagem in self.mensagens_pendentes.pop(nome):
                time.sleep(0.5) #dar uma diferenciada
                conexao.send(mensagem.encode(FORMATO))
                
            print(f"[SERVIDOR] Mensagens pendendes foram entregues para {nome}")
    
    

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
            
            self.enviar_mensagens_pendentes(nome, conexao)
            
            
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

    def aguardar_novos_usuarios(self):
        pass

    def tratar_servidor(self):
        while True:
            try:
                msg = input()
                if msg == "-off":
                    os._exit(0)
            except Exception as e:
                os._exit(0)
       

    def iniciar_servidor(self):
        servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        servidor.bind(ENDERECO)
        servidor.listen()

        print(f"[SERVIDOR] Ouvindo em {ENDERECO}:")

        try:
            thread_servidor = threading.Thread(target=self.tratar_servidor)
            thread_servidor.start()
        except Exception as e:
            traceback.print_exc(e)
            os._exit(0)
        
        while True:
            conexao, endereco = servidor.accept()
            processo_cliente = threading.Thread(target=self.tratar_cliente, args=(conexao, endereco))
            processo_cliente.start()

            
            print(f"[CONEXÃO ACEITA] Conexão ativa com {endereco}")


if __name__ == "__main__":
    Server()