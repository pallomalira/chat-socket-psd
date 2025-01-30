class User:

    def __init__(self, nome, socket):
        self.nome = nome
        self.socket = socket
        self.is_online = True

    def __str__(self):
        return f"nome: {self.nome}, socket: {self.socket}, is_online: {self.is_online}"
