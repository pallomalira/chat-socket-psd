import socket
import os
import traceback
import datetime
import threading
from model import Cliente, MensagemGrupoPendente
import time

IP_SERVIDOR = "127.0.0.1"
PORTA = 5050
ENDERECO = (IP_SERVIDOR, PORTA)
FORMATO = 'utf-8'


class Server:

    clientes = {}
    grupos = {}
    mensagens_privadas_pendentes = {}
    mensagens_grupos_pendentes = {}

    def __init__(self):
        self.iniciar_servidor()

    #Iniciando o servidor (atuação do server)
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

    def tratar_servidor(self):
        while True:
            try:
                msg = input()
                if msg == "-off":
                    os._exit(0)
            except Exception as e:
                os._exit(0)      

    #Iniciando conexão com o cliente (atuação Cliente - Servidor)
    def tratar_cliente(self, conexao, endereco):
        try:
            while True:
                nome = conexao.recv(1024).decode(FORMATO)
                if nome in self.clientes and self.clientes[nome].is_online:
                    conexao.send("[ERRO] Nome já em uso, escolha outro: ".encode(FORMATO))
                else:
                    conexao.send("[SUCESSO] Você está conectado!".encode(FORMATO))
                    break
            if nome in self.clientes.keys():
                self.clientes[nome].is_online = True
            else:
                self.clientes[nome] = Cliente(nome, conexao)
            print(f"[NOVA CONEXÃO] {nome} conectado do {endereco}")
            
            self.enviar_mensagens_grupos_pendentes(nome, conexao)
            self.enviar_mensagens_privadas_pendentes(nome, conexao)
            
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
                # self.clientes.pop(nome)
                self.clientes[nome].is_online = False
            conexao.close()

    def processar_comando(self, comando, nome, conexao):
        if comando.startswith("-msg "):
           
            partes = comando.split(" ", 3)
            print(partes)
            if len(partes) < 4:
               conexao.send("[ERRO] Comando inválido. Formato correto:\n -msg U NICK MENSAGEM ou \n -msg G GRUPO MENSAGEM".encode(FORMATO))
               return

            tipo, destinatarios, mensagem = partes[1], partes[2], partes[3]
            destinatarios = destinatarios.strip("[]").split(",")
            if tipo == "U": 
                for destinatario in destinatarios:
                    mensagem_formatada = self.formatar_mensagem(nome, "", mensagem)
                    if destinatario in self.clientes and self.clientes[destinatario].is_online:
                        self.enviar_mensagem(nome, destinatario, mensagem_formatada)
                    else:
                        self.guardar_mensagens_privadas_pendentes(destinatario, mensagem_formatada)

            elif tipo == "G": 
                try:
                    # só deve ser possível enviar se o usuário estiver no grupo
                    if nome in self.grupos[destinatarios[0]]:
                        if destinatarios[0] in self.grupos:
                            membros_offline = []
                            for membro in self.grupos[destinatarios[0]]:
                                mensagem_formatada = self.formatar_mensagem(nome, destinatarios[0], mensagem)
                                
                                if membro in self.clientes and self.clientes[membro].is_online:
                                    self.enviar_mensagem(nome, membro, mensagem_formatada)
                                else:
                                    membros_offline.append(membro)
                            if membros_offline:
                                self.guardar_mensagens_grupos_pendentes(destinatarios[0], membros_offline, mensagem_formatada)
                        else:
                            conexao.send("[ERRO] Grupo não encontrado.".encode(FORMATO))
                    else:
                            conexao.send("[ERRO] Você não está neste grupo.".encode(FORMATO))
                except Exception as e:
                    print(e)

            else:
                conexao.send("[ERRO] Tipo inválido. Use 'U' para usuário ou 'G' para grupo.".encode(FORMATO))
                
        else: 
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

    def enviar_mensagem(self, remetente, destinatario, mensagem):
        try:
            if remetente != destinatario:
                self.clientes[destinatario].conexao.send(mensagem.encode(FORMATO))
                print(f"[SERVIDOR] {remetente} enviou mensagem para {destinatario}: {mensagem}")
        except Exception as e:
            print(f"[ERRO] Não foi possível enviar para {destinatario}")
            self.clientes.pop(destinatario, None)

    def formatar_mensagem(self, nick, grupo, mensagem):
            hora_atual = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            if grupo:
                return f"({nick}, {grupo}, {hora_atual}) {mensagem}"
            return f"({nick}) {mensagem}"

    #Tratamentos dos Comandos
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
            self.grupos[args][nome] = Cliente(nome, conexao)
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

    #armazemanento offline
    def guardar_mensagens_privadas_pendentes(self, nome_usuario, mensagem):
        # criar um armazenamento de grupo e privado separados, pois o armazenamento em grupo deve ser enviado para todos os usuários do grupo que estiverem online e offline. Ou seja, enquando todos não receberem, não podemos excluir da base.
        if nome_usuario not in self.mensagens_privadas_pendentes:
            self.mensagens_privadas_pendentes[nome_usuario] = []

        self.mensagens_privadas_pendentes[nome_usuario].append(mensagem)
        print(f"[MENSAGEM PENDENTE] Mensagem para {nome_usuario} armazenada.")

    def guardar_mensagens_grupos_pendentes(self, grupo: str, membros: list, mensagem: str):
        # criar um armazenamento de grupo e privado separados, pois o armazenamento em grupo deve ser enviado para todos os usuários do grupo que estiverem online e offline. Ou seja, enquando todos não receberem, não podemos excluir da base.
        if grupo not in self.mensagens_grupos_pendentes:
            self.mensagens_grupos_pendentes[grupo] = []

        self.mensagens_grupos_pendentes[grupo].append(MensagemGrupoPendente(grupo, membros, mensagem))
        print(f"[MENSAGEM PENDENTE] Mensagem para {grupo} armazenada.")

    def enviar_mensagens_grupos_pendentes(self, nome, conexao):
        membro_in_grupos = []
        for grupo, membros in self.grupos.items():
            if nome in membros:
                membro_in_grupos.append(grupo)
       # Somente para os grupos em que o membro está cadastrado é que eu olho se tem mensagens pendentes;
        for grupo_cadastrado in membro_in_grupos:
            # somente se o grupo em que ele está cadastrado tiver mensagens pendentes é que ele envia
            if self.mensagens_grupos_pendentes.get(grupo_cadastrado, None):
                
                #verifica as mgs pendentes
                for mensagem_pendente in self.mensagens_grupos_pendentes[grupo_cadastrado]:
                    
                    
                        for membro in mensagem_pendente.membros:
                            if membro == nome:
                                time.sleep(0.5)
                                conexao.send(mensagem_pendente.mensagem.encode(FORMATO))
                                mensagem_pendente.membros.remove(nome)
                
                #verifica se há mensagens vazias
                i = 0
                while i < len(self.mensagens_grupos_pendentes[grupo_cadastrado]):
                    if not mensagem_pendente.membros:
                        self.mensagens_grupos_pendentes[grupo_cadastrado].pop(i)
                    else:
                        i += 1

    def enviar_mensagens_privadas_pendentes(self, nome, conexao):
        if nome in self.mensagens_privadas_pendentes:
            for mensagem in self.mensagens_privadas_pendentes.pop(nome):
                time.sleep(0.5) #dar uma diferenciada
                conexao.send(mensagem.encode(FORMATO))
                
            print(f"[SERVIDOR] Mensagens pendendes foram entregues para {nome}")


if __name__ == "__main__":
    Server()
