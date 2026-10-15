"""Camada de dados - SQLite (arquivo local, sem servidor).
Usa ? como parâmetro, separando SQL dos dados.
Cada usuário tem seu próprio estoque (coluna usuario_id).

O arquivo do banco fica ao lado deste módulo (cantina.db). Para guardá-lo em outro
lugar (ex.: um disco persistente na hospedagem), defina a variável SQLITE_PATH.
"""
import hashlib
import os
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime

DB_PATH = os.environ.get(
    "SQLITE_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "cantina.db"))
DB_NAME = os.path.basename(DB_PATH)
DIAS_ALERTA_VALIDADE = 7

# datas guardadas como texto ISO e devolvidas como date / datetime
sqlite3.register_adapter(date, lambda d: d.isoformat())
sqlite3.register_adapter(datetime, lambda d: d.isoformat(sep=" "))
sqlite3.register_converter("DATE", lambda b: date.fromisoformat(b.decode()))
sqlite3.register_converter("DATETIME", lambda b: datetime.fromisoformat(b.decode()))


def _dict_factory(cur, row):
    return {d[0]: v for d, v in zip(cur.description, row)}


def conectar():
    con = sqlite3.connect(DB_PATH, timeout=10, detect_types=sqlite3.PARSE_DECLTYPES,
                          isolation_level=None)  # autocommit; transações são explícitas
    con.row_factory = _dict_factory
    con.execute("PRAGMA foreign_keys = ON")
    return con


@contextmanager
def _transacao():
    """BEGIN IMMEDIATE trava a escrita: evita duas vendas simultâneas estourarem o estoque."""
    con = conectar()
    try:
        con.execute("BEGIN IMMEDIATE")
        yield con
        con.execute("COMMIT")
    except BaseException:
        if con.in_transaction:
            con.execute("ROLLBACK")
        raise
    finally:
        con.close()


def criar_banco():
    con = conectar()
    try:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                usuario TEXT NOT NULL UNIQUE,
                senha_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                criado_em DATETIME NOT NULL DEFAULT (datetime('now','localtime'))
            );
            CREATE TABLE IF NOT EXISTS produtos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER REFERENCES usuarios(id),
                nome TEXT NOT NULL,
                categoria TEXT NOT NULL,
                quantidade INTEGER NOT NULL DEFAULT 0 CHECK (quantidade >= 0),
                estoque_minimo INTEGER NOT NULL DEFAULT 0,
                validade DATE NULL,
                preco REAL NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS movimentacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER REFERENCES usuarios(id),
                produto_id INTEGER NOT NULL REFERENCES produtos(id) ON DELETE RESTRICT,
                tipo TEXT NOT NULL CHECK (tipo IN ('entrada','saida')),
                quantidade INTEGER NOT NULL CHECK (quantidade > 0),
                validade_lote DATE NULL,
                observacao TEXT NULL,
                data DATETIME NOT NULL DEFAULT (datetime('now','localtime')),
                valor_unit REAL NOT NULL DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_produtos_usuario ON produtos(usuario_id);
            CREATE INDEX IF NOT EXISTS idx_mov_produto ON movimentacoes(produto_id);
        """)
    finally:
        con.close()


# ================= USUÁRIOS / LOGIN =================
def _hash(senha, salt):
    return hashlib.pbkdf2_hmac("sha256", senha.encode(), bytes.fromhex(salt), 120_000).hex()


def registrar_usuario(nome, usuario, senha):
    nome, usuario = nome.strip(), usuario.strip().lower()
    if not nome or not usuario or not senha:
        return False, "Preencha todos os campos"
    if len(senha) < 4:
        return False, "A senha deve ter pelo menos 4 caracteres"
    try:
        with _transacao() as con:
            if con.execute("SELECT id FROM usuarios WHERE usuario=?", (usuario,)).fetchone():
                return False, "Este usuário já existe"
            salt = os.urandom(16).hex()
            cur = con.execute("INSERT INTO usuarios(nome,usuario,senha_hash,salt) VALUES(?,?,?,?)",
                              (nome, usuario, _hash(senha, salt), salt))
            novo_id = cur.lastrowid
            # primeira conta assume produtos antigos (sem dono)
            if con.execute("SELECT COUNT(*) AS n FROM usuarios").fetchone()["n"] == 1:
                con.execute("UPDATE produtos SET usuario_id=? WHERE usuario_id IS NULL", (novo_id,))
                con.execute("UPDATE movimentacoes SET usuario_id=? WHERE usuario_id IS NULL", (novo_id,))
        return True, "Conta criada com sucesso"
    except Exception as e:
        return False, f"Erro ao criar conta: {e}"


def autenticar(usuario, senha):
    con = conectar()
    try:
        u = con.execute("SELECT * FROM usuarios WHERE usuario=?", (usuario.strip().lower(),)).fetchone()
    finally:
        con.close()
    if not u or _hash(senha, u["salt"]) != u["senha_hash"]:
        return None
    return {"id": u["id"], "nome": u["nome"], "usuario": u["usuario"]}


def alterar_senha(uid, atual, nova):
    with _transacao() as con:
        u = con.execute("SELECT * FROM usuarios WHERE id=?", (uid,)).fetchone()
        if not u or _hash(atual, u["salt"]) != u["senha_hash"]:
            return False, "Senha atual incorreta"
        if len(nova) < 4:
            return False, "A nova senha deve ter pelo menos 4 caracteres"
        salt = os.urandom(16).hex()
        con.execute("UPDATE usuarios SET senha_hash=?, salt=? WHERE id=?", (_hash(nova, salt), salt, uid))
    return True, "Senha alterada"


# ================= CREATE =================
def cadastrar_produto(uid, nome, categoria, estoque_minimo, validade=None, preco=0):
    with _transacao() as con:
        con.execute("INSERT INTO produtos(usuario_id,nome,categoria,quantidade,estoque_minimo,validade,preco) "
                    "VALUES(?,?,?,0,?,?,?)", (uid, nome, categoria, estoque_minimo, validade, preco))
    return True, "Produto cadastrado"


def registrar_entrada(uid, produto_id, quantidade, validade_lote=None, obs=""):
    if quantidade <= 0:
        return False, "Quantidade deve ser maior que zero"
    try:
        with _transacao() as con:
            row = con.execute("SELECT validade FROM produtos WHERE id=? AND usuario_id=?",
                              (produto_id, uid)).fetchone()
            if not row:
                return False, "Produto não encontrado"
            con.execute("UPDATE produtos SET quantidade=quantidade+? WHERE id=?", (quantidade, produto_id))
            if validade_lote and (row["validade"] is None or validade_lote < row["validade"]):
                con.execute("UPDATE produtos SET validade=? WHERE id=?", (validade_lote, produto_id))
            con.execute("INSERT INTO movimentacoes(usuario_id,produto_id,tipo,quantidade,validade_lote,observacao) "
                        "VALUES(?,?,'entrada',?,?,?)", (uid, produto_id, quantidade, validade_lote, obs))
        return True, "Entrada registrada"
    except Exception as e:
        return False, str(e)


# ================= UPDATE =================
def registrar_saida(uid, produto_id, quantidade, obs=""):
    if quantidade <= 0:
        return False, "Quantidade deve ser maior que zero"
    try:
        with _transacao() as con:
            atual = con.execute("SELECT quantidade, preco FROM produtos WHERE id=? AND usuario_id=?",
                                (produto_id, uid)).fetchone()
            if not atual or atual["quantidade"] < quantidade:
                return False, "Estoque insuficiente"
            con.execute("UPDATE produtos SET quantidade=quantidade-? WHERE id=?", (quantidade, produto_id))
            con.execute("INSERT INTO movimentacoes(usuario_id,produto_id,tipo,quantidade,observacao,valor_unit) "
                        "VALUES(?,?,'saida',?,?,?)", (uid, produto_id, quantidade, obs, atual["preco"]))
        return True, "Saída registrada"
    except Exception as e:
        return False, str(e)


def editar_produto(uid, produto_id, nome, categoria, estoque_minimo, validade=None, preco=0):
    with _transacao() as con:
        con.execute("UPDATE produtos SET nome=?,categoria=?,estoque_minimo=?,validade=?,preco=? "
                    "WHERE id=? AND usuario_id=?",
                    (nome, categoria, estoque_minimo, validade, preco, produto_id, uid))
    return True, "Produto atualizado"


# ================= DELETE =================
def excluir_produto(uid, produto_id):
    with _transacao() as con:
        if con.execute("SELECT COUNT(*) AS n FROM movimentacoes WHERE produto_id=?",
                       (produto_id,)).fetchone()["n"] > 0:
            return False, "Produto possui histórico de movimentações e não pode ser excluído"
        apagados = con.execute("DELETE FROM produtos WHERE id=? AND usuario_id=?",
                               (produto_id, uid)).rowcount
    return (True, "Produto excluído") if apagados else (False, "Produto não encontrado")


# ================= READ =================
def _consulta(sql, params=()):
    con = conectar()
    try:
        return con.execute(sql, params).fetchall()
    finally:
        con.close()


def listar_produtos(uid, busca=""):
    like = f"%{busca}%"
    return _consulta("SELECT * FROM produtos WHERE usuario_id=? AND (nome LIKE ? OR categoria LIKE ?) "
                     "ORDER BY nome COLLATE NOCASE", (uid, like, like))


def obter_produto(uid, produto_id):
    r = _consulta("SELECT * FROM produtos WHERE id=? AND usuario_id=?", (produto_id, uid))
    return r[0] if r else None


def listar_movimentacoes(uid, busca=""):
    like = f"%{busca}%"
    return _consulta("""
        SELECT m.id, p.nome, m.tipo, m.quantidade, m.validade_lote, m.observacao, m.data, m.valor_unit
        FROM movimentacoes m JOIN produtos p ON p.id = m.produto_id
        WHERE p.usuario_id=? AND (p.nome LIKE ? OR m.tipo LIKE ?)
        ORDER BY m.data DESC, m.id DESC""", (uid, like, like))


def itens_baixos(uid):
    return _consulta("SELECT * FROM produtos WHERE usuario_id=? AND quantidade <= estoque_minimo "
                     "ORDER BY quantidade", (uid,))


def proximos_vencimento(uid, dias=DIAS_ALERTA_VALIDADE):
    return _consulta("SELECT *, CAST(julianday(validade) - julianday(date('now','localtime')) AS INTEGER) AS dias "
                     "FROM produtos WHERE usuario_id=? AND validade IS NOT NULL AND quantidade > 0 "
                     "AND validade <= date('now','localtime', ?) ORDER BY validade",
                     (uid, f"+{int(dias)} days"))


def resumo(uid):
    r = _consulta("SELECT COUNT(*) AS total, COALESCE(SUM(quantidade),0) AS unidades "
                  "FROM produtos WHERE usuario_id=?", (uid,))[0]
    vendido = _consulta("SELECT COALESCE(SUM(m.quantidade*m.valor_unit),0) AS v FROM movimentacoes m "
                        "JOIN produtos p ON p.id=m.produto_id WHERE p.usuario_id=? AND m.tipo='saida'",
                        (uid,))[0]["v"]
    return {"produtos": r["total"], "unidades": int(r["unidades"]), "vendido": float(vendido),
            "baixos": len(itens_baixos(uid)), "vencendo": len(proximos_vencimento(uid))}
