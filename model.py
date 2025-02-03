class Cliente:

    def __init__(self, nome, conexao):
        self.nome = nome
        self.conexao = conexao
        self.is_online = True

    def __str__(self):
        return f"nome: {self.nome}, conexao: {self.conexao}, is_online: {self.is_online}"

class MensagemGrupoPendente:

    def __init__(self, grupo: str, membros: list, mensagem: str,):
        self.grupo = grupo
        self.membros = membros
        self.mensagem = mensagem

    def __str__(self):
        return f"grupo: {self.grupo}, membros: {self.membros}, mensagem: {self.mensagem}"
    
    def __repr__(self):
        return f"MensagemPendente(grupo: {self.grupo}, membros: {self.membros}, mensagem: {self.mensagem})"
