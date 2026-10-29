"""
database.py — SQLite Persistence Layer & Business Logic (harErp)
================================================================
Dual-inventory ERP architecture integrated with financial cash flow:
  - ingredientes              → Raw materials / inputs (with weighted average cost calculation)
  - receitas                  → Recipes / Bill of Materials (yield, default shelf life, selling price)
  - lotes_produto             → Finished product batches created via manufacturing orders
  - saidas_lote               → Batch outflows / sales (by specific batch or automatic FEFO)
  - movimentacoes_financeiras → Financial cash flow (revenues and expenses)

Dates are stored as ISO strings (YYYY-MM-DD).
"""

import csv
import math
import os
import sqlite3
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def load_env(env_path=None):
    """Loads key=value pairs from .env into os.environ without external dependencies."""
    path = env_path or os.path.join(BASE_DIR, ".env")
    if not os.path.exists(path):
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = val
    except OSError:
        pass


load_env()

_env_db = os.environ.get("HARERP_DB_PATH", "estoque.db").strip() or "estoque.db"
DB_PATH = _env_db if os.path.isabs(_env_db) else os.path.join(BASE_DIR, _env_db)
EXPIRY_WARNING_DAYS = int(os.environ.get("HARERP_EXPIRY_WARNING_DAYS", "7") or 7)


def conectar():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def hoje():
    return datetime.now().strftime("%Y-%m-%d")


# ─────────────────────────────────────────────────────────────────────────────
# CRIAÇÃO / MIGRAÇÃO DE TABELAS
# ─────────────────────────────────────────────────────────────────────────────

def _garantir_coluna(cursor, tabela, coluna, definicao):
    """Adiciona coluna na tabela caso ainda não exista (migração segura)."""
    cols = [r[1] for r in cursor.execute(f"PRAGMA table_info({tabela})").fetchall()]
    if coluna not in cols:
        cursor.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {definicao}")


def criar_tabelas():
    conn = conectar()
    c = conn.cursor()

    # Ingredientes (insumos / matérias-primas)
    c.execute("""
        CREATE TABLE IF NOT EXISTS ingredientes (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            nome            TEXT    NOT NULL,
            marca           TEXT    DEFAULT '',
            categoria       TEXT    DEFAULT '',
            quantidade      REAL    NOT NULL DEFAULT 0,
            estoque_minimo  REAL    NOT NULL DEFAULT 0,
            unidade         TEXT    DEFAULT 'un',
            preco_custo     REAL    NOT NULL DEFAULT 0,
            data_cadastro   TEXT    NOT NULL
        )
    """)

    # Movimentações de ingredientes
    c.execute("""
        CREATE TABLE IF NOT EXISTS mov_ingredientes (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            ingrediente_id INTEGER NOT NULL,
            tipo           TEXT    NOT NULL CHECK(tipo IN ('entrada','saida')),
            quantidade     REAL    NOT NULL,
            data           TEXT    NOT NULL,
            observacao     TEXT    DEFAULT '',
            FOREIGN KEY (ingrediente_id) REFERENCES ingredientes(id) ON DELETE CASCADE
        )
    """)

    # Receitas (fichas técnicas)
    c.execute("""
        CREATE TABLE IF NOT EXISTS receitas (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            nome          TEXT    NOT NULL,
            rendimento    INTEGER NOT NULL DEFAULT 1,
            validade_dias INTEGER DEFAULT NULL,
            preco_venda   REAL    NOT NULL DEFAULT 0,
            observacao    TEXT    DEFAULT ''
        )
    """)
    _garantir_coluna(c, "receitas", "validade_dias", "INTEGER DEFAULT NULL")
    _garantir_coluna(c, "receitas", "preco_venda", "REAL NOT NULL DEFAULT 0")

    # Componentes de cada receita
    c.execute("""
        CREATE TABLE IF NOT EXISTS receita_ingredientes (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            receita_id     INTEGER NOT NULL,
            ingrediente_id INTEGER NOT NULL,
            quantidade     REAL    NOT NULL,
            FOREIGN KEY (receita_id)     REFERENCES receitas(id)     ON DELETE CASCADE,
            FOREIGN KEY (ingrediente_id) REFERENCES ingredientes(id) ON DELETE CASCADE
        )
    """)

    # Lotes de produto acabado
    c.execute("""
        CREATE TABLE IF NOT EXISTS lotes_produto (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            receita_id            INTEGER NOT NULL,
            quantidade_total      INTEGER NOT NULL,
            quantidade_disponivel INTEGER NOT NULL,
            custo_total           REAL    NOT NULL,
            data_fabricacao       TEXT    NOT NULL,
            data_vencimento       TEXT    DEFAULT NULL,
            observacao            TEXT    DEFAULT '',
            FOREIGN KEY (receita_id) REFERENCES receitas(id) ON DELETE CASCADE
        )
    """)

    # Saídas de lote (vendas/baixas)
    c.execute("""
        CREATE TABLE IF NOT EXISTS saidas_lote (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            lote_id        INTEGER NOT NULL,
            quantidade     INTEGER NOT NULL,
            preco_unitario REAL    NOT NULL DEFAULT 0,
            valor_total    REAL    NOT NULL DEFAULT 0,
            data           TEXT    NOT NULL,
            observacao     TEXT    DEFAULT '',
            FOREIGN KEY (lote_id) REFERENCES lotes_produto(id) ON DELETE CASCADE
        )
    """)
    _garantir_coluna(c, "saidas_lote", "preco_unitario", "REAL NOT NULL DEFAULT 0")
    _garantir_coluna(c, "saidas_lote", "valor_total", "REAL NOT NULL DEFAULT 0")

    # Financeiro
    c.execute("""
        CREATE TABLE IF NOT EXISTS movimentacoes_financeiras (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo      TEXT NOT NULL CHECK(tipo IN ('receita','despesa')),
            categoria TEXT DEFAULT '',
            descricao TEXT DEFAULT '',
            valor     REAL NOT NULL,
            data      TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# INGREDIENTES
# ─────────────────────────────────────────────────────────────────────────────

def adicionar_ingrediente(nome, marca, categoria, quantidade,
                           estoque_minimo, unidade, preco_custo):
    conn = conectar()
    cur = conn.execute("""
        INSERT INTO ingredientes
            (nome, marca, categoria, quantidade, estoque_minimo, unidade, preco_custo, data_cadastro)
        VALUES (?,?,?,?,?,?,?,?)
    """, (nome, marca, categoria, quantidade, estoque_minimo, unidade, preco_custo, hoje()))
    novo_id = cur.lastrowid
    if quantidade > 0:
        conn.execute("""
            INSERT INTO mov_ingredientes (ingrediente_id, tipo, quantidade, data, observacao)
            VALUES (?, 'entrada', ?, ?, 'Estoque inicial no cadastro')
        """, (novo_id, quantidade, hoje()))
    conn.commit()
    conn.close()
    return novo_id


def listar_ingredientes(termo=None):
    conn = conectar()
    if termo:
        cur = conn.execute("""
            SELECT * FROM ingredientes
            WHERE nome LIKE ? OR marca LIKE ? OR categoria LIKE ?
            ORDER BY nome
        """, (f"%{termo}%",) * 3)
    else:
        cur = conn.execute("SELECT * FROM ingredientes ORDER BY nome")
    rows = cur.fetchall()
    conn.close()
    return rows


def obter_ingrediente(iid):
    conn = conectar()
    row = conn.execute("SELECT * FROM ingredientes WHERE id=?", (iid,)).fetchone()
    conn.close()
    return row


def atualizar_ingrediente(iid, nome, marca, categoria,
                           estoque_minimo, unidade, preco_custo):
    conn = conectar()
    conn.execute("""
        UPDATE ingredientes
        SET nome=?, marca=?, categoria=?, estoque_minimo=?, unidade=?, preco_custo=?
        WHERE id=?
    """, (nome, marca, categoria, estoque_minimo, unidade, preco_custo, iid))
    conn.commit()
    conn.close()


def excluir_ingrediente(iid):
    conn = conectar()
    conn.execute("DELETE FROM ingredientes WHERE id=?", (iid,))
    conn.commit()
    conn.close()


def ingredientes_abaixo_minimo():
    conn = conectar()
    rows = conn.execute("""
        SELECT * FROM ingredientes WHERE quantidade <= estoque_minimo ORDER BY nome
    """).fetchall()
    conn.close()
    return rows


def registrar_mov_ingrediente(iid, tipo, quantidade, observacao="",
                               novo_custo=None, lancar_financeiro=False):
    if tipo not in ("entrada", "saida"):
        raise ValueError("tipo deve ser 'entrada' ou 'saida'")
    if quantidade <= 0:
        raise ValueError("quantidade deve ser maior que zero")
    conn = conectar()
    atual = conn.execute(
        "SELECT nome, unidade, quantidade, preco_custo FROM ingredientes WHERE id=?",
        (iid,)
    ).fetchone()
    if atual is None:
        conn.close()
        raise ValueError("Ingrediente não encontrado")

    qtd_atual = atual["quantidade"]
    custo_atual = atual["preco_custo"]
    nova_qtd = round(qtd_atual + quantidade if tipo == "entrada" else qtd_atual - quantidade, 6)
    if nova_qtd < 0:
        conn.close()
        raise ValueError("Estoque insuficiente para essa saída")

    custo_final = custo_atual
    custo_operacao = custo_atual
    if tipo == "entrada" and novo_custo is not None and novo_custo > 0:
        custo_operacao = novo_custo
        if qtd_atual > 0 and nova_qtd > 0:
            custo_final = round(((qtd_atual * custo_atual) + (quantidade * novo_custo)) / nova_qtd, 4)
        else:
            custo_final = round(novo_custo, 4)

    conn.execute("""
        INSERT INTO mov_ingredientes (ingrediente_id, tipo, quantidade, data, observacao)
        VALUES (?,?,?,?,?)
    """, (iid, tipo, round(quantidade, 6), hoje(), observacao))
    conn.execute(
        "UPDATE ingredientes SET quantidade=?, preco_custo=? WHERE id=?",
        (nova_qtd, custo_final, iid)
    )

    if tipo == "entrada" and lancar_financeiro:
        valor_compra = round(quantidade * custo_operacao, 2)
        if valor_compra > 0:
            desc = f"Compra de {round(quantidade, 4)} {atual['unidade']} de {atual['nome']}"
            if observacao:
                desc += f" ({observacao})"
            conn.execute("""
                INSERT INTO movimentacoes_financeiras (tipo, categoria, descricao, valor, data)
                VALUES ('despesa', 'Compra de Insumos', ?, ?, ?)
            """, (desc, valor_compra, hoje()))

    conn.commit()
    conn.close()


def listar_mov_ingredientes(iid=None):
    conn = conectar()
    if iid:
        cur = conn.execute("""
            SELECT m.*, i.nome AS ingrediente_nome, i.unidade
            FROM mov_ingredientes m JOIN ingredientes i ON i.id=m.ingrediente_id
            WHERE m.ingrediente_id=? ORDER BY m.data DESC, m.id DESC
        """, (iid,))
    else:
        cur = conn.execute("""
            SELECT m.*, i.nome AS ingrediente_nome, i.unidade
            FROM mov_ingredientes m JOIN ingredientes i ON i.id=m.ingrediente_id
            ORDER BY m.data DESC, m.id DESC
        """)
    rows = cur.fetchall()
    conn.close()
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# RECEITAS (FICHAS TÉCNICAS)
# ─────────────────────────────────────────────────────────────────────────────

def salvar_receita(nome, rendimento, observacao, componentes,
                   receita_id=None, validade_dias=None, preco_venda=0.0):
    """
    componentes: lista de dicts {ingrediente_id, quantidade}
    Retorna o id da receita salva.
    """
    conn = conectar()
    if receita_id is None:
        cur = conn.execute("""
            INSERT INTO receitas (nome, rendimento, validade_dias, preco_venda, observacao)
            VALUES (?,?,?,?,?)
        """, (nome, rendimento, validade_dias, preco_venda, observacao))
        receita_id = cur.lastrowid
    else:
        conn.execute("""
            UPDATE receitas
            SET nome=?, rendimento=?, validade_dias=?, preco_venda=?, observacao=?
            WHERE id=?
        """, (nome, rendimento, validade_dias, preco_venda, observacao, receita_id))
        conn.execute("DELETE FROM receita_ingredientes WHERE receita_id=?", (receita_id,))

    for c in componentes:
        conn.execute("""
            INSERT INTO receita_ingredientes (receita_id, ingrediente_id, quantidade)
            VALUES (?,?,?)
        """, (receita_id, c["ingrediente_id"], c["quantidade"]))
    conn.commit()
    conn.close()
    return receita_id


def listar_receitas():
    conn = conectar()
    rows = conn.execute("SELECT * FROM receitas ORDER BY nome").fetchall()
    conn.close()
    return rows


def obter_receita(receita_id):
    conn = conectar()
    rec = conn.execute("SELECT * FROM receitas WHERE id=?", (receita_id,)).fetchone()
    comps = conn.execute("""
        SELECT ri.*, i.nome AS ingrediente_nome, i.preco_custo,
               i.quantidade AS estoque_atual, i.unidade
        FROM receita_ingredientes ri
        JOIN ingredientes i ON i.id=ri.ingrediente_id
        WHERE ri.receita_id=?
    """, (receita_id,)).fetchall()
    conn.close()
    return rec, list(comps)


def excluir_receita(receita_id):
    conn = conectar()
    conn.execute("DELETE FROM receitas WHERE id=?", (receita_id,))
    conn.commit()
    conn.close()


def calcular_custo_receita(receita_id):
    """Retorna (custo_por_lote, custo_por_unidade)."""
    rec, comps = obter_receita(receita_id)
    if rec is None:
        return 0.0, 0.0
    custo_lote = sum(c["preco_custo"] * c["quantidade"] for c in comps)
    rend = rec["rendimento"] or 1
    return custo_lote, custo_lote / rend


def analise_rentabilidade_receitas():
    """Retorna lista de dicts com análise de custo, preço de venda e margem de cada receita."""
    receitas = listar_receitas()
    resultado = []
    for r in receitas:
        _, comps = obter_receita(r["id"])
        custo_lote = sum(c["preco_custo"] * c["quantidade"] for c in comps)
        rend = r["rendimento"] or 1
        custo_unit = custo_lote / rend
        preco_venda = r["preco_venda"] or 0.0
        lucro_unit = preco_venda - custo_unit if preco_venda > 0 else 0.0
        margem_pct = ((lucro_unit / preco_venda) * 100.0) if preco_venda > 0 else 0.0
        resultado.append({
            "id": r["id"],
            "nome": r["nome"],
            "rendimento": rend,
            "validade_dias": r["validade_dias"],
            "n_ingredientes": len(comps),
            "custo_lote": custo_lote,
            "custo_unitario": custo_unit,
            "preco_venda": preco_venda,
            "lucro_unitario": lucro_unit,
            "margem_percentual": margem_pct,
        })
    return resultado


def simular_producao_e_compras(receita_id, lotes_desejados=1):
    """
    Analisa a capacidade de produção da receita com o estoque atual e gera
    a Lista de Compras caso faltem insumos para `lotes_desejados`.
    """
    rec, comps = obter_receita(receita_id)
    if rec is None or not comps:
        return {
            "receita_nome": "",
            "rendimento": 1,
            "lotes_desejados": lotes_desejados,
            "unidades_desejadas": 0,
            "max_lotes_possiveis": 0,
            "max_unidades_possiveis": 0,
            "gargalo": None,
            "viavel": False,
            "custo_reposicao_total": 0.0,
            "itens": [],
        }

    lotes_desejados = max(1, int(lotes_desejados))
    max_lotes = None
    gargalo = None
    itens = []
    custo_reposicao_total = 0.0

    for c in comps:
        qtd_por_lote = float(c["quantidade"])
        disp = float(c["estoque_atual"])
        custo_un = float(c["preco_custo"])
        possivel_ing = int(math.floor(disp / qtd_por_lote)) if qtd_por_lote > 0 else 999999
        if max_lotes is None or possivel_ing < max_lotes:
            max_lotes = possivel_ing
            gargalo = c["ingrediente_nome"]

        necessario = round(qtd_por_lote * lotes_desejados, 4)
        falta = round(max(0.0, necessario - disp), 4)
        custo_rep = round(falta * custo_un, 2)
        custo_reposicao_total += custo_rep
        itens.append({
            "ingrediente_id": c["ingrediente_id"],
            "ingrediente_nome": c["ingrediente_nome"],
            "unidade": c["unidade"] or "un",
            "qtd_por_lote": qtd_por_lote,
            "necessario": necessario,
            "disponivel": round(disp, 4),
            "falta_comprar": falta,
            "preco_custo": custo_un,
            "custo_reposicao": custo_rep,
        })

    return {
        "receita_nome": rec["nome"],
        "rendimento": rec["rendimento"],
        "lotes_desejados": lotes_desejados,
        "unidades_desejadas": rec["rendimento"] * lotes_desejados,
        "max_lotes_possiveis": max_lotes or 0,
        "max_unidades_possiveis": (max_lotes or 0) * rec["rendimento"],
        "gargalo": gargalo,
        "viavel": (max_lotes or 0) >= lotes_desejados,
        "custo_reposicao_total": round(custo_reposicao_total, 2),
        "itens": itens,
    }


# ─────────────────────────────────────────────────────────────────────────────
# FABRICAÇÃO (LOTES DE PRODUTO ACABADO) E SAÍDAS / FEFO
# ─────────────────────────────────────────────────────────────────────────────

def fabricar_lote(receita_id, lotes, data_vencimento=None, observacao=""):
    """
    Executa a fabricação:
      - Verifica e subtrai ingredientes do estoque
      - Cria um novo lote em lotes_produto
    Retorna (lote_id, unidades_produzidas, custo_total).
    Lança ValueError se algum ingrediente estiver em falta.
    """
    rec, comps = obter_receita(receita_id)
    if rec is None:
        raise ValueError("Receita não encontrada")
    if lotes <= 0:
        raise ValueError("Número de lotes deve ser > 0")

    if not data_vencimento and rec["validade_dias"]:
        try:
            dias = int(rec["validade_dias"])
            if dias > 0:
                data_vencimento = (datetime.now().date() + timedelta(days=dias)).strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            pass

    custo_lote, _ = calcular_custo_receita(receita_id)
    custo_total = custo_lote * lotes
    unidades = rec["rendimento"] * lotes

    conn = conectar()

    # Verifica antes de alterar qualquer coisa
    for c in comps:
        necessario = round(c["quantidade"] * lotes, 6)
        atual = conn.execute(
            "SELECT quantidade FROM ingredientes WHERE id=?", (c["ingrediente_id"],)
        ).fetchone()["quantidade"]
        if atual < necessario:
            conn.close()
            raise ValueError(
                f"Estoque insuficiente: '{c['ingrediente_nome']}' — "
                f"necessário {necessario} {c['unidade']}, disponível {atual} {c['unidade']}"
            )

    # Baixa ingredientes
    for c in comps:
        necessario = round(c["quantidade"] * lotes, 6)
        conn.execute(
            "UPDATE ingredientes SET quantidade=ROUND(quantidade-?, 6) WHERE id=?",
            (necessario, c["ingrediente_id"])
        )
        conn.execute("""
            INSERT INTO mov_ingredientes (ingrediente_id, tipo, quantidade, data, observacao)
            VALUES (?, 'saida', ?, ?, ?)
        """, (c["ingrediente_id"], necessario, hoje(),
              f"Fabricação: {rec['nome']} — {lotes} lote(s)"))

    # Cria lote de produto
    cur = conn.execute("""
        INSERT INTO lotes_produto
            (receita_id, quantidade_total, quantidade_disponivel,
             custo_total, data_fabricacao, data_vencimento, observacao)
        VALUES (?,?,?,?,?,?,?)
    """, (receita_id, unidades, unidades, custo_total, hoje(), data_vencimento, observacao))
    lote_id = cur.lastrowid

    conn.commit()
    conn.close()
    return lote_id, unidades, custo_total


def listar_lotes(receita_id=None, apenas_ativos=False):
    conn = conectar()
    cond = []
    params = []
    if receita_id:
        cond.append("l.receita_id=?")
        params.append(receita_id)
    if apenas_ativos:
        cond.append("l.quantidade_disponivel>0")
    where = ("WHERE " + " AND ".join(cond)) if cond else ""
    cur = conn.execute(f"""
        SELECT l.*, r.nome AS receita_nome, r.preco_venda AS preco_venda_sugerido,
               ROUND(l.custo_total * 1.0 / CASE WHEN l.quantidade_total > 0 THEN l.quantidade_total ELSE 1 END, 4) AS custo_unitario
        FROM lotes_produto l
        JOIN receitas r ON r.id=l.receita_id
        {where}
        ORDER BY l.data_fabricacao DESC, l.id DESC
    """, params)
    rows = cur.fetchall()
    conn.close()
    return rows


def registrar_saida_lote(lote_id, quantidade, observacao="",
                          preco_unitario=None, lancar_financeiro=False):
    if quantidade <= 0:
        raise ValueError("quantidade deve ser > 0")
    conn = conectar()
    lote = conn.execute("""
        SELECT l.quantidade_disponivel, l.receita_id, r.nome AS receita_nome, r.preco_venda
        FROM lotes_produto l
        JOIN receitas r ON r.id = l.receita_id
        WHERE l.id=?
    """, (lote_id,)).fetchone()
    if lote is None:
        conn.close()
        raise ValueError("Lote não encontrado")
    if lote["quantidade_disponivel"] < quantidade:
        conn.close()
        raise ValueError(
            f"Disponível apenas {lote['quantidade_disponivel']} unidade(s)"
        )

    preco_un = preco_unitario if (preco_unitario is not None and preco_unitario >= 0) else (lote["preco_venda"] or 0.0)
    valor_total = round(quantidade * preco_un, 2)

    conn.execute("""
        UPDATE lotes_produto SET quantidade_disponivel=quantidade_disponivel-? WHERE id=?
    """, (quantidade, lote_id))
    conn.execute("""
        INSERT INTO saidas_lote (lote_id, quantidade, preco_unitario, valor_total, data, observacao)
        VALUES (?,?,?,?,?,?)
    """, (lote_id, quantidade, preco_un, valor_total, hoje(), observacao))

    if lancar_financeiro and valor_total > 0:
        desc = f"Venda Lote #{lote_id} ({quantidade}x {lote['receita_nome']})"
        if observacao:
            desc += f" — {observacao}"
        conn.execute("""
            INSERT INTO movimentacoes_financeiras (tipo, categoria, descricao, valor, data)
            VALUES ('receita', 'Venda de Produtos', ?, ?, ?)
        """, (desc, valor_total, hoje()))

    conn.commit()
    conn.close()


def registrar_saida_fefo(receita_id, quantidade, observacao="",
                         preco_unitario=None, lancar_financeiro=False):
    """
    Registra saída/venda automática por FEFO (First-Expired, First-Out):
    baixa primeiro dos lotes com vencimento mais próximo (não vencidos).
    Retorna lista de (lote_id, qtd_baixada).
    """
    if quantidade <= 0:
        raise ValueError("A quantidade deve ser maior que zero.")

    conn = conectar()
    rec = conn.execute("SELECT * FROM receitas WHERE id=?", (receita_id,)).fetchone()
    if rec is None:
        conn.close()
        raise ValueError("Receita não encontrada.")

    data_hoje = hoje()
    lotes = conn.execute("""
        SELECT * FROM lotes_produto
        WHERE receita_id=? AND quantidade_disponivel > 0
          AND (data_vencimento IS NULL OR data_vencimento >= ?)
        ORDER BY
          CASE WHEN data_vencimento IS NULL THEN 1 ELSE 0 END ASC,
          data_vencimento ASC,
          id ASC
    """, (receita_id, data_hoje)).fetchall()

    disp_total = sum(l["quantidade_disponivel"] for l in lotes)
    if disp_total < quantidade:
        conn.close()
        raise ValueError(
            f"Estoque disponível insuficiente (não vencido) para '{rec['nome']}': "
            f"solicitado {quantidade} un., disponível {disp_total} un."
        )

    preco_un = preco_unitario if (preco_unitario is not None and preco_unitario >= 0) else (rec["preco_venda"] or 0.0)
    restante = int(quantidade)
    baixas = []

    for l in lotes:
        if restante <= 0:
            break
        usar = min(restante, int(l["quantidade_disponivel"]))
        val_parcial = round(usar * preco_un, 2)
        conn.execute(
            "UPDATE lotes_produto SET quantidade_disponivel=quantidade_disponivel-? WHERE id=?",
            (usar, l["id"])
        )
        obs_lote = f"[FEFO] {observacao}".strip()
        conn.execute("""
            INSERT INTO saidas_lote (lote_id, quantidade, preco_unitario, valor_total, data, observacao)
            VALUES (?,?,?,?,?,?)
        """, (l["id"], usar, preco_un, val_parcial, data_hoje, obs_lote))
        baixas.append((l["id"], usar))
        restante -= usar

    valor_total_venda = round(quantidade * preco_un, 2)
    if lancar_financeiro and valor_total_venda > 0:
        lotes_str = ", ".join(f"#{lid}({q}un)" for lid, q in baixas)
        desc = f"Venda FEFO {quantidade}x {rec['nome']} [Lotes: {lotes_str}]"
        if observacao:
            desc += f" — {observacao}"
        conn.execute("""
            INSERT INTO movimentacoes_financeiras (tipo, categoria, descricao, valor, data)
            VALUES ('receita', 'Venda de Produtos', ?, ?, ?)
        """, (desc, valor_total_venda, data_hoje))

    conn.commit()
    conn.close()
    return baixas


def listar_saidas_lote(lote_id=None):
    conn = conectar()
    if lote_id:
        cur = conn.execute("""
            SELECT s.*, r.nome AS receita_nome
            FROM saidas_lote s
            JOIN lotes_produto l ON l.id=s.lote_id
            JOIN receitas r ON r.id=l.receita_id
            WHERE s.lote_id=?
            ORDER BY s.data DESC, s.id DESC
        """, (lote_id,))
    else:
        cur = conn.execute("""
            SELECT s.*, r.nome AS receita_nome
            FROM saidas_lote s
            JOIN lotes_produto l ON l.id=s.lote_id
            JOIN receitas r ON r.id=l.receita_id
            ORDER BY s.data DESC, s.id DESC
        """)
    rows = cur.fetchall()
    conn.close()
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# FINANCEIRO
# ─────────────────────────────────────────────────────────────────────────────

def adicionar_movimentacao_financeira(tipo, categoria, descricao, valor, data=None):
    if tipo not in ("receita", "despesa"):
        raise ValueError("tipo inválido")
    if valor <= 0:
        raise ValueError("valor deve ser > 0")
    conn = conectar()
    conn.execute("""
        INSERT INTO movimentacoes_financeiras (tipo, categoria, descricao, valor, data)
        VALUES (?,?,?,?,?)
    """, (tipo, categoria, descricao, valor, data or hoje()))
    conn.commit()
    conn.close()


def atualizar_movimentacao_financeira(mov_id, tipo, categoria, descricao, valor, data):
    if tipo not in ("receita", "despesa"):
        raise ValueError("tipo inválido")
    if valor <= 0:
        raise ValueError("valor deve ser > 0")
    conn = conectar()
    conn.execute("""
        UPDATE movimentacoes_financeiras
        SET tipo=?, categoria=?, descricao=?, valor=?, data=?
        WHERE id=?
    """, (tipo, categoria, descricao, valor, data, mov_id))
    conn.commit()
    conn.close()


def obter_movimentacao_financeira(mov_id):
    conn = conectar()
    row = conn.execute("SELECT * FROM movimentacoes_financeiras WHERE id=?", (mov_id,)).fetchone()
    conn.close()
    return row


def excluir_movimentacao_financeira(mov_id):
    conn = conectar()
    conn.execute("DELETE FROM movimentacoes_financeiras WHERE id=?", (mov_id,))
    conn.commit()
    conn.close()


def listar_movimentacoes_financeiras(data_inicio=None, data_fim=None, tipo=None, termo=None):
    conn = conectar()
    q = "SELECT * FROM movimentacoes_financeiras"
    cond, params = [], []
    if data_inicio:
        cond.append("data>=?")
        params.append(data_inicio)
    if data_fim:
        cond.append("data<=?")
        params.append(data_fim)
    if tipo in ("receita", "despesa"):
        cond.append("tipo=?")
        params.append(tipo)
    if termo:
        cond.append("(categoria LIKE ? OR descricao LIKE ?)")
        params.extend([f"%{termo}%", f"%{termo}%"])
    if cond:
        q += " WHERE " + " AND ".join(cond)
    q += " ORDER BY data DESC, id DESC"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return rows


def saldo_atual():
    conn = conectar()
    rec = conn.execute(
        "SELECT COALESCE(SUM(valor),0) AS t FROM movimentacoes_financeiras WHERE tipo='receita'"
    ).fetchone()["t"]
    desp = conn.execute(
        "SELECT COALESCE(SUM(valor),0) AS t FROM movimentacoes_financeiras WHERE tipo='despesa'"
    ).fetchone()["t"]
    conn.close()
    return rec, desp, rec - desp


def fluxo_caixa_mensal():
    conn = conectar()
    cur = conn.execute("""
        SELECT substr(data,1,7) AS mes,
               SUM(CASE WHEN tipo='receita' THEN valor ELSE 0 END) AS receitas,
               SUM(CASE WHEN tipo='despesa' THEN valor ELSE 0 END) AS despesas
        FROM movimentacoes_financeiras
        GROUP BY mes ORDER BY mes
    """)
    rows = [(r["mes"], r["receitas"], r["despesas"]) for r in cur.fetchall()]
    conn.close()
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# ESTATÍSTICAS / ANÁLISE (BI DASHBOARD)
# ─────────────────────────────────────────────────────────────────────────────

def custo_total_ingredientes_estoque():
    conn = conectar()
    val = conn.execute(
        "SELECT COALESCE(SUM(preco_custo*quantidade),0) AS t FROM ingredientes"
    ).fetchone()["t"]
    conn.close()
    return val


def custo_total_lotes_estoque():
    """Retorna o valor de custo proporcional dos produtos acabados atualmente em estoque."""
    conn = conectar()
    val = conn.execute("""
        SELECT COALESCE(SUM((custo_total * 1.0 / quantidade_total) * quantidade_disponivel), 0) AS t
        FROM lotes_produto
        WHERE quantidade_disponivel > 0 AND quantidade_total > 0
    """).fetchone()["t"]
    conn.close()
    return val


def lotes_alertas_vencimento(dias_aviso=None):
    """Retorna (vencidos, vencendo) dentre os lotes com saldo disponível."""
    if dias_aviso is None:
        dias_aviso = EXPIRY_WARNING_DAYS
    lotes = listar_lotes(apenas_ativos=True)
    data_hoje = datetime.now().date()
    vencidos, vencendo = [], []
    for l in lotes:
        venc = l["data_vencimento"]
        if not venc:
            continue
        try:
            dv = datetime.strptime(venc, "%Y-%m-%d").date()
            delta = (dv - data_hoje).days
            if delta < 0:
                vencidos.append(l)
            elif delta <= dias_aviso:
                vencendo.append(l)
        except ValueError:
            pass
    return vencidos, vencendo


def estoque_ingredientes_resumo():
    conn = conectar()
    rows = conn.execute("""
        SELECT nome, quantidade, estoque_minimo, preco_custo,
               ROUND(preco_custo*quantidade,2) AS valor_total
        FROM ingredientes ORDER BY nome
    """).fetchall()
    conn.close()
    return rows


def evolucao_mov_ingredientes():
    """Retorna [(data, acumulado)] de entradas/saidas de ingredientes."""
    conn = conectar()
    rows = conn.execute("""
        SELECT data,
               SUM(CASE WHEN tipo='entrada' THEN quantidade ELSE -quantidade END) AS delta
        FROM mov_ingredientes GROUP BY data ORDER BY data
    """).fetchall()
    conn.close()
    result, acc = [], 0
    for r in rows:
        acc += r["delta"]
        result.append((r["data"], acc))
    return result


def resumo_lotes_produto():
    """Retorna totais de unidades fabricadas, disponíveis e saídas por receita."""
    conn = conectar()
    rows = conn.execute("""
        SELECT r.nome AS receita,
               COALESCE(SUM(l.quantidade_total),0)      AS fabricadas,
               COALESCE(SUM(l.quantidade_disponivel),0) AS disponivel,
               COALESCE(SUM(l.quantidade_total - l.quantidade_disponivel),0) AS saidas
        FROM receitas r
        LEFT JOIN lotes_produto l ON l.receita_id=r.id
        GROUP BY r.id ORDER BY r.nome
    """).fetchall()
    conn.close()
    return rows


def despesas_por_categoria(data_inicio=None, data_fim=None):
    """Retorna [(categoria, total)] das despesas no período."""
    conn = conectar()
    cond = ["tipo='despesa'"]
    params = []
    if data_inicio:
        cond.append("data>=?")
        params.append(data_inicio)
    if data_fim:
        cond.append("data<=?")
        params.append(data_fim)
    where = "WHERE " + " AND ".join(cond)
    rows = conn.execute(f"""
        SELECT COALESCE(NULLIF(TRIM(categoria),''), 'Sem Categoria') AS cat,
               SUM(valor) AS total
        FROM movimentacoes_financeiras
        {where}
        GROUP BY cat
        ORDER BY total DESC
    """, params).fetchall()
    conn.close()
    return [(r["cat"], r["total"]) for r in rows]


def desempenho_vendas_por_receita(data_inicio=None, data_fim=None):
    """Retorna faturamento, CMV, lucro bruto e unidades vendidas por receita."""
    conn = conectar()
    cond, params = [], []
    if data_inicio:
        cond.append("s.data>=?")
        params.append(data_inicio)
    if data_fim:
        cond.append("s.data<=?")
        params.append(data_fim)
    where = ("WHERE " + " AND ".join(cond)) if cond else ""
    rows = conn.execute(f"""
        SELECT r.nome AS receita,
               COALESCE(SUM(s.quantidade), 0) AS unidades_vendidas,
               COALESCE(SUM(s.valor_total), 0) AS faturamento,
               COALESCE(SUM(s.quantidade * (l.custo_total * 1.0 / CASE WHEN l.quantidade_total > 0 THEN l.quantidade_total ELSE 1 END)), 0) AS cmv
        FROM saidas_lote s
        JOIN lotes_produto l ON l.id = s.lote_id
        JOIN receitas r ON r.id = l.receita_id
        {where}
        GROUP BY r.id
        ORDER BY faturamento DESC
    """, params).fetchall()
    conn.close()
    resultado = []
    for r in rows:
        fat = r["faturamento"]
        cmv = r["cmv"]
        lucro = fat - cmv
        resultado.append({
            "receita": r["receita"],
            "unidades": r["unidades_vendidas"],
            "faturamento": fat,
            "cmv": cmv,
            "lucro": lucro,
        })
    return resultado


def indicadores_dashboard(data_inicio=None, data_fim=None):
    """Calcula conjunto abrangente de KPIs financeiros, de estoque, produção e vendas."""
    conn = conectar()
    rec_global, desp_global, saldo_global = saldo_atual()

    cond_f, params_f = [], []
    if data_inicio:
        cond_f.append("data>=?")
        params_f.append(data_inicio)
    if data_fim:
        cond_f.append("data<=?")
        params_f.append(data_fim)
    where_f = ("WHERE " + " AND ".join(cond_f)) if cond_f else ""
    fin_row = conn.execute(f"""
        SELECT
            COALESCE(SUM(CASE WHEN tipo='receita' THEN valor ELSE 0 END), 0) AS rec_periodo,
            COALESCE(SUM(CASE WHEN tipo='despesa' THEN valor ELSE 0 END), 0) AS desp_periodo,
            SUM(CASE WHEN tipo='receita' THEN 1 ELSE 0 END) AS n_rec,
            SUM(CASE WHEN tipo='despesa' THEN 1 ELSE 0 END) AS n_desp
        FROM movimentacoes_financeiras
        {where_f}
    """, params_f).fetchone()

    rec_per = fin_row["rec_periodo"] or 0.0
    desp_per = fin_row["desp_periodo"] or 0.0
    res_per = rec_per - desp_per
    margem_caixa = ((res_per / rec_per) * 100.0) if rec_per > 0 else 0.0

    ing_row = conn.execute("""
        SELECT COUNT(*) AS total_itens,
               COALESCE(SUM(preco_custo * quantidade), 0) AS capital_insumos,
               SUM(CASE WHEN quantidade <= estoque_minimo THEN 1 ELSE 0 END) AS itens_alerta
        FROM ingredientes
    """).fetchone()

    lotes_row = conn.execute("""
        SELECT COUNT(CASE WHEN l.quantidade_disponivel > 0 THEN 1 END) AS lotes_ativos,
               COALESCE(SUM(l.quantidade_total), 0) AS total_produzido,
               COALESCE(SUM(l.quantidade_disponivel), 0) AS total_disponivel,
               COALESCE(SUM(CASE WHEN l.quantidade_disponivel > 0 AND l.quantidade_total > 0
                            THEN (l.custo_total * 1.0 / l.quantidade_total) * l.quantidade_disponivel
                            ELSE 0 END), 0) AS custo_lotes_ativos,
               COALESCE(SUM(CASE WHEN l.quantidade_disponivel > 0
                            THEN l.quantidade_disponivel * COALESCE(r.preco_venda, 0)
                            ELSE 0 END), 0) AS venda_potencial_lotes
        FROM lotes_produto l
        JOIN receitas r ON r.id = l.receita_id
    """).fetchone()

    cond_s, params_s = [], []
    if data_inicio:
        cond_s.append("s.data>=?")
        params_s.append(data_inicio)
    if data_fim:
        cond_s.append("s.data<=?")
        params_s.append(data_fim)
    where_s = ("WHERE " + " AND ".join(cond_s)) if cond_s else ""
    vendas_row = conn.execute(f"""
        SELECT COALESCE(SUM(s.quantidade), 0) AS un_vendidas,
               COALESCE(SUM(s.valor_total), 0) AS faturamento_lotes,
               COALESCE(SUM(s.quantidade * (l.custo_total * 1.0 / CASE WHEN l.quantidade_total > 0 THEN l.quantidade_total ELSE 1 END)), 0) AS cmv_lotes
        FROM saidas_lote s
        JOIN lotes_produto l ON l.id = s.lote_id
        {where_s}
    """, params_s).fetchone()

    conn.close()

    fat_lotes = vendas_row["faturamento_lotes"] or 0.0
    cmv_lotes = vendas_row["cmv_lotes"] or 0.0
    lucro_bruto_vendas = fat_lotes - cmv_lotes
    margem_bruta_vendas = ((lucro_bruto_vendas / fat_lotes) * 100.0) if fat_lotes > 0 else 0.0

    tot_prod = lotes_row["total_produzido"] or 0
    tot_disp = lotes_row["total_disponivel"] or 0
    tot_escoado = tot_prod - tot_disp
    giro_producao = ((tot_escoado / tot_prod) * 100.0) if tot_prod > 0 else 0.0

    return {
        "saldo_global": saldo_global,
        "rec_global": rec_global,
        "desp_global": desp_global,
        "rec_periodo": rec_per,
        "desp_periodo": desp_per,
        "resultado_periodo": res_per,
        "margem_caixa": margem_caixa,
        "n_rec": fin_row["n_rec"] or 0,
        "n_desp": fin_row["n_desp"] or 0,
        "total_insumos": ing_row["total_itens"] or 0,
        "capital_insumos": ing_row["capital_insumos"] or 0.0,
        "insumos_alerta": ing_row["itens_alerta"] or 0,
        "lotes_ativos": lotes_row["lotes_ativos"] or 0,
        "total_produzido": tot_prod,
        "total_disponivel": tot_disp,
        "total_escoado": tot_escoado,
        "giro_producao": giro_producao,
        "custo_lotes_ativos": lotes_row["custo_lotes_ativos"] or 0.0,
        "venda_potencial_lotes": lotes_row["venda_potencial_lotes"] or 0.0,
        "un_vendidas_periodo": vendas_row["un_vendidas"] or 0,
        "faturamento_lotes": fat_lotes,
        "cmv_lotes": cmv_lotes,
        "lucro_bruto_vendas": lucro_bruto_vendas,
        "margem_bruta_vendas": margem_bruta_vendas,
    }


# ─────────────────────────────────────────────────────────────────────────────
# BACKUP, RESTAURAÇÃO, CSV E DADOS DE DEMONSTRAÇÃO (SEED)
# ─────────────────────────────────────────────────────────────────────────────

def fazer_backup(caminho_destino):
    """Realiza backup seguro do banco SQLite para o arquivo de destino."""
    origem = conectar()
    destino = sqlite3.connect(caminho_destino)
    with destino:
        origem.backup(destino)
    destino.close()
    origem.close()
    return caminho_destino


def restaurar_backup(caminho_origem):
    """Valida integridade de um arquivo .db e restaura sobre o banco ativo."""
    if not os.path.exists(caminho_origem):
        raise ValueError("Arquivo de backup não encontrado.")

    teste = sqlite3.connect(caminho_origem)
    try:
        status = teste.execute("PRAGMA integrity_check").fetchone()[0]
        if status != "ok":
            raise ValueError(f"Arquivo de banco corrompido: {status}")
        tabelas = {
            r[0] for r in teste.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        if not {"ingredientes", "receitas", "movimentacoes_financeiras"}.issubset(tabelas):
            raise ValueError(
                "The selected file does not contain harErp database tables."
            )
    finally:
        teste.close()

    origem = sqlite3.connect(caminho_origem)
    destino = sqlite3.connect(DB_PATH)
    with destino:
        origem.backup(destino)
    destino.close()
    origem.close()
    criar_tabelas()
    return DB_PATH


def exportar_csv_tabelas(diretorio_destino):
    """Exports core database tables to UTF-8-BOM CSV files."""
    os.makedirs(diretorio_destino, exist_ok=True)
    arquivos = []

    # 1. Ingredients
    cam_ing = os.path.join(diretorio_destino, "harerp_ingredients.csv")
    with open(cam_ing, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["ID", "Name", "Brand", "Category", "Unit", "Quantity", "Min Stock", "Unit Cost", "Created Date"])
        for r in listar_ingredientes():
            w.writerow([r["id"], r["nome"], r["marca"], r["categoria"], r["unidade"], r["quantidade"], r["estoque_minimo"], r["preco_custo"], r["data_cadastro"]])
    arquivos.append(cam_ing)

    # 2. Recipes
    cam_rec = os.path.join(diretorio_destino, "harerp_recipes.csv")
    with open(cam_rec, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["ID", "Name", "Yield", "Shelf Life Days", "Batch Cost", "Unit Cost", "Selling Price", "Margin %"])
        for r in analise_rentabilidade_receitas():
            w.writerow([r["id"], r["nome"], r["rendimento"], r["validade_dias"] or "", round(r["custo_lote"], 4), round(r["custo_unitario"], 4), round(r["preco_venda"], 2), round(r["margem_percentual"], 2)])
    arquivos.append(cam_rec)

    # 3. Batches
    cam_lot = os.path.join(diretorio_destino, "harerp_batches.csv")
    with open(cam_lot, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["ID", "Recipe", "Produced Date", "Expiration Date", "Total Qty", "Available Qty", "Total Cost", "Unit Cost", "Notes"])
        for l in listar_lotes():
            w.writerow([l["id"], l["receita_nome"], l["data_fabricacao"], l["data_vencimento"] or "", l["quantidade_total"], l["quantidade_disponivel"], round(l["custo_total"], 2), round(l["custo_unitario"], 4), l["observacao"]])
    arquivos.append(cam_lot)

    # 4. Finance
    cam_fin = os.path.join(diretorio_destino, "harerp_finance.csv")
    with open(cam_fin, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["ID", "Date", "Type", "Category", "Description", "Amount"])
        for m in listar_movimentacoes_financeiras():
            w.writerow([m["id"], m["data"], m["tipo"], m["categoria"], m["descricao"], round(m["valor"], 2)])
    arquivos.append(cam_fin)

    return arquivos


def popular_dados_exemplo():
    """Insere um conjunto rico de dados de demonstração (evita duplicatas se já carregado)."""
    criar_tabelas()
    existentes = {i["nome"]: i["id"] for i in listar_ingredientes()}
    if "Farinha de Trigo Especial" in existentes and "Brownie Artesanal Intenso" in {r["nome"] for r in listar_receitas()}:
        return False

    # 1. Ingredientes
    i_farinha = adicionar_ingrediente("Farinha de Trigo Especial", "Dona Benta", "Secos", 25.0, 5.0, "kg", 5.80)
    i_acucar  = adicionar_ingrediente("Açúcar Refinado", "União", "Secos", 15.0, 4.0, "kg", 4.50)
    i_choc    = adicionar_ingrediente("Chocolate Meio Amargo 50%", "Callebaut", "Chocolates", 8.0, 3.0, "kg", 48.00)
    i_manteiga= adicionar_ingrediente("Manteiga Sem Sal", "Aviação", "Laticínios", 6.0, 2.0, "kg", 38.00)
    i_ovos    = adicionar_ingrediente("Ovos Grandes", "Granja Ouro", "Perecíveis", 120.0, 30.0, "un", 0.75)
    i_emb     = adicionar_ingrediente("Embalagem Kraft Individual", "PackEco", "Embalagens", 15.0, 20.0, "un", 1.10)

    # 2. Receitas
    r_brownie = salvar_receita(
        nome="Brownie Artesanal Intenso",
        rendimento=12,
        observacao="Assar a 180°C por 25 minutos",
        validade_dias=7,
        preco_venda=12.00,
        componentes=[
            {"ingrediente_id": i_choc,     "quantidade": 0.40},
            {"ingrediente_id": i_manteiga, "quantidade": 0.25},
            {"ingrediente_id": i_acucar,   "quantidade": 0.30},
            {"ingrediente_id": i_farinha,  "quantidade": 0.20},
            {"ingrediente_id": i_ovos,     "quantidade": 4.0},
            {"ingrediente_id": i_emb,      "quantidade": 2.0},
        ]
    )
    r_cookie = salvar_receita(
        nome="Cookie Clássico com Gotas de Chocolate",
        rendimento=10,
        observacao="Massa descansada 24h na geladeira",
        validade_dias=10,
        preco_venda=9.50,
        componentes=[
            {"ingrediente_id": i_farinha,  "quantidade": 0.30},
            {"ingrediente_id": i_manteiga, "quantidade": 0.15},
            {"ingrediente_id": i_acucar,   "quantidade": 0.20},
            {"ingrediente_id": i_choc,     "quantidade": 0.25},
            {"ingrediente_id": i_ovos,     "quantidade": 2.0},
        ]
    )

    # 3. Fabricação de lotes e vendas
    lote1_id, _, _ = fabricar_lote(r_brownie, 2, observacao="Produção começo da semana")
    lote2_id, _, _ = fabricar_lote(r_cookie,  3, observacao="Lote vitrine e encomendas")

    registrar_saida_lote(lote1_id, 15, observacao="Venda balcão e delivery", preco_unitario=12.00, lancar_financeiro=True)
    registrar_saida_lote(lote2_id, 18, observacao="Encomenda cafeteria parceira", preco_unitario=9.50, lancar_financeiro=True)

    # 4. Movimentações financeiras complementares
    mes_passado = (datetime.now().date().replace(day=1) - timedelta(days=10)).strftime("%Y-%m-%d")
    adicionar_movimentacao_financeira("receita", "Vendas Mensais", "Fechamento quinzena anterior", 1450.00, mes_passado)
    adicionar_movimentacao_financeira("despesa", "Compra de Insumos", "Reposição estoque inicial", 680.00, mes_passado)
    adicionar_movimentacao_financeira("despesa", "Custos Fixos", "Energia elétrica e gás", 240.00, hoje())
    return True
