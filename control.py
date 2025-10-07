
import variaveis_globais
from requesicao import requestBD

def chamar(sql):
    try:
        resp = requestBD(sql)
        if isinstance(resp, dict) and 'payload' in resp and resp.get('ok', False):
            return resp.get('payload')
        if isinstance(resp, dict) and resp.get('error'):
            return None
        return resp
    except Exception:
        return None

class ControllerUsuario:


    def inserir_usuario(self, nome, senha):
        sql = (f"INSERT INTO Usuario (nome, senha) VALUES('{nome}', '{senha}');")
        return chamar(sql)

    def listar_usuario(self, nome='', senha = ''):
        sql = f"SELECT * FROM Usuario WHERE nome LIKE '{nome}' AND senha LIKE '{senha}';"
        return chamar(sql)

    def excluir_usuario(self, id):
        sql = f"DELETE FROM Usuario WHERE id={id};"
        return chamar(sql)

    def editar_usuario(self, id, nome, senha):
        sql = f"UPDATE cliente SET nome='{nome}', senha='{senha}' WHERE id={id};"
        return chamar(sql)

    def editar_sala(self):
        id = variaveis_globais.lista_global[0][0]
        sql = f"UPDATE Usuario SET sala_id = (SELECT MAX(id) FROM Sala) WHERE id = {id};"
        return chamar(sql)

    def associar_usuario_sala(self, usuario_id, sala_id):
        try:
            sql = f"UPDATE Usuario SET sala_id = {sala_id} WHERE id = {usuario_id};"
            return chamar(sql)
        except Exception as e:
            return None
    
class ControllerSala:

    def inserir_sala(self):
        sql = (f"INSERT INTO Sala DEFAULT VALUES;")
        return chamar(sql)

    def listar_sala(self, id=''):
        sql = f"SELECT * FROM Sala WHERE id LIKE '{id}';"
        return chamar(sql)

    def excluir_sala(self, id):
        sql = f"DELETE FROM Sala WHERE id={id};"
        return chamar(sql)

    def listar_jogadores(self, sala_id):
        sql = f"SELECT id, nome FROM Usuario WHERE sala_id = {sala_id};"
        return chamar(sql)

    def iniciar_partida(self, sala_id):
        sql = f"UPDATE Sala SET started = 1 WHERE id = {sala_id};"
        return chamar(sql)

    # lista mensagens do chat
    def listar_chat(self, sala_id, limit=200):
        sql = f"SELECT usuario, mensagem, ts FROM Chat WHERE sala_id = {sala_id} ORDER BY ts ASC LIMIT {limit};"
        return chamar(sql)

    def inserir_chat(self, sala_id, usuario, mensagem, ts=None):
        if ts is None:
            ts = ''
        u = str(usuario).replace("'", "''")
        m = str(mensagem).replace("'", "''")
        if ts:
            s = str(ts).replace("'", "''")
            sql = "INSERT INTO Chat (sala_id, usuario, mensagem, ts) VALUES ({}, '{}', '{}', '{}');".format(sala_id, u, m, s)
        else:
            sql = "INSERT INTO Chat (sala_id, usuario, mensagem) VALUES ({}, '{}', '{}');".format(sala_id, u, m)
        return chamar(sql)


class ControllerFrase:
    def inserir_frase(self, texto, criado_em=None):
        if criado_em is None:
            criado_em = ''
        safe = str(texto).replace("'", "''")
        ts = criado_em
        if ts:
            s = str(ts).replace("'", "''")
            sql = "INSERT INTO Frase (texto, criado_em) VALUES ('{}','{}');".format(safe, s)
        else:
            sql = "INSERT INTO Frase (texto) VALUES ('{}');".format(safe)
        return chamar(sql)


class ControllerAlbum:
    def listar_sequencia(self, album_id):
        sql = f"SELECT tipo, conteudo, autor FROM AlbumSequencia WHERE album_id = {album_id} ORDER BY ordem;"
        return chamar(sql)


class ControllerRanking:
    def listar_ranking(self, limit=50):
        sql = f"SELECT id, titulo, usuario, score FROM Ranking ORDER BY score DESC LIMIT {limit};"
        return chamar(sql)


