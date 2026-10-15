"""Cantina — controle de estoque com login (Streamlit + SQLite).

Rodar com:  streamlit run app.py
"""
import html
from datetime import date, datetime

import streamlit as st

import database as db

st.set_page_config(page_title="Cantina — Estoque", page_icon="🍽️", layout="wide")

st.markdown(
    """
<style>
.badge{display:inline-block;padding:2px 10px;border-radius:999px;font-size:.72rem;
       font-weight:600;margin-left:8px;vertical-align:middle}
.badge.danger{background:#3a1a26;color:#f2627a}
.badge.warn{background:#3a2d14;color:#f5b041}
.pnome{font-size:1.05rem;font-weight:700;letter-spacing:.2px}
.psub{color:#8a97b0;font-size:.85rem}
.pval{color:#93b8ff;font-size:.9rem;white-space:nowrap}
.pval.venc{color:#f2627a}
.pqtd{font-size:1.25rem;font-weight:700;text-align:center}
.pqtd.baixo{color:#f2627a}
.mov{font-size:1.4rem;font-weight:700;text-align:center}
.mov.ent{color:#2dd4b0}
.mov.sai{color:#f2627a}
.avatar{display:inline-flex;align-items:center;justify-content:center;width:44px;height:44px;
        border-radius:50%;background:#3b82f6;color:#fff;font-weight:700;margin-right:12px}
</style>
""",
    unsafe_allow_html=True,
)

PAGINAS = ["⌂  Início", "▢  Produtos", "↗  Vendas", "⚙  Configurações"]


# ======================= HELPERS =======================
def moeda(v):
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_data(d, curto=False):
    if not d:
        return "--/--/--" if curto else ""
    return d.strftime("%d/%m/%y" if curto else "%d/%m/%Y")


def iniciais(nome):
    p = nome.split()
    return (p[0][0] + (p[-1][0] if len(p) > 1 else p[0][1:2])).upper()


def esc(txt):
    return html.escape(str(txt))


def situacao(p):
    """(texto, tipo) ou None se estiver tudo normal."""
    if p["validade"] and p["quantidade"] > 0:
        d = (p["validade"] - date.today()).days
        if d < 0:
            return "Vencido", "danger"
        if d <= db.DIAS_ALERTA_VALIDADE:
            return f"Vence em {d}d", "warn"
    if p["quantidade"] <= p["estoque_minimo"]:
        return "Estoque baixo", "danger"
    return None


def aviso(msg):
    """Mensagem que sobrevive ao st.rerun()."""
    st.session_state["_toast"] = msg


def abrir(tipo, *args):
    """Agenda a abertura de um diálogo e recarrega a página."""
    st.session_state["_dlg"] = (tipo, *args)
    st.rerun()


@st.cache_resource(show_spinner="Conectando ao banco...")
def iniciar_banco():
    db.criar_banco()
    return True


# ======================= LOGIN =======================
def tela_login():
    _, centro, _ = st.columns([1, 1.3, 1])
    with centro:
        st.markdown("# 🍽️ Cantina")
        aba_entrar, aba_criar = st.tabs(["Entrar", "Criar conta"])

        with aba_entrar:
            st.caption("Entre para acessar seu estoque")
            with st.form("form_login"):
                usuario = st.text_input("Usuário", placeholder="ex.: maria")
                senha = st.text_input("Senha", type="password")
                enviar = st.form_submit_button("Entrar", type="primary")
            if enviar:
                try:
                    u = db.autenticar(usuario, senha)
                except Exception as e:
                    st.error(f"Erro de conexão com o banco: {e}")
                    return
                if u:
                    st.session_state["usuario"] = u
                    st.rerun()
                st.error("Usuário ou senha incorretos")

        with aba_criar:
            st.caption("Cada conta tem o próprio estoque e histórico")
            with st.form("form_registro"):
                nome = st.text_input("Nome completo", placeholder="Como você quer ser chamado")
                usuario = st.text_input("Usuário", placeholder="ex.: maria", key="reg_usuario")
                senha = st.text_input("Senha", type="password", key="reg_senha")
                conf = st.text_input("Confirmar senha", type="password")
                criar = st.form_submit_button("Criar conta", type="primary")
            if criar:
                if senha != conf:
                    st.error("As senhas não coincidem")
                    return
                try:
                    ok, msg = db.registrar_usuario(nome, usuario, senha)
                    if not ok:
                        st.error(msg)
                        return
                    u = db.autenticar(usuario, senha)
                except Exception as e:
                    st.error(f"Erro de conexão com o banco: {e}")
                    return
                if u:
                    st.session_state["usuario"] = u
                    st.rerun()


# ======================= DIÁLOGOS =======================
def _form_produto(uid, pid):
    p = db.obter_produto(uid, pid) if pid else None
    st.caption("Atualize o cadastro" if p else "O estoque começa em zero — use “Entrada” depois.")
    with st.form("f_produto"):
        nome = st.text_input("Nome", value=p["nome"] if p else "", placeholder="Ex.: Suco de laranja")
        cat = st.text_input("Categoria", value=p["categoria"] if p else "", placeholder="Ex.: Bebidas")
        preco = st.number_input("Preço de venda (R$)", min_value=0.0, step=0.5, format="%.2f",
                                value=float(p["preco"]) if p else 0.0)
        mini = st.number_input("Estoque mínimo", min_value=0, step=1,
                               value=int(p["estoque_minimo"]) if p else 0)
        val = st.date_input("Validade (opcional)", value=p["validade"] if p else None,
                            min_value=date(2000, 1, 1), max_value=date(2100, 12, 31),
                            format="DD/MM/YYYY")
        salvar = st.form_submit_button("Salvar" if p else "Cadastrar", type="primary")
    if salvar:
        if not nome.strip() or not cat.strip():
            st.error("Nome e categoria são obrigatórios.")
            return
        if p:
            ok, msg = db.editar_produto(uid, pid, nome.strip(), cat.strip(), int(mini), val, float(preco))
        else:
            ok, msg = db.cadastrar_produto(uid, nome.strip(), cat.strip(), int(mini), val, float(preco))
        aviso(msg)
        st.rerun()


def _form_mov(uid, tipo, pid):
    ent = tipo == "entrada"
    produtos = db.listar_produtos(uid)
    if not produtos:
        st.info("Cadastre um produto primeiro.")
        return
    st.caption("Recebimento de mercadoria (novo lote)" if ent else "Venda ou baixa de estoque")
    ids = [p["id"] for p in produtos]
    mapa = {p["id"]: p for p in produtos}
    with st.form("f_mov"):
        escolhido = st.selectbox("Produto", ids, index=ids.index(pid) if pid in ids else 0,
                                 format_func=lambda i: f'{mapa[i]["nome"]} — {mapa[i]["quantidade"]} un.')
        qtd = st.number_input("Quantidade", min_value=1, step=1, value=1)
        val = None
        if ent:
            val = st.date_input("Validade do lote (opcional)", value=None,
                                min_value=date(2000, 1, 1), max_value=date(2100, 12, 31),
                                format="DD/MM/YYYY")
        obs = st.text_input("Observação", placeholder="Opcional")
        ok_btn = st.form_submit_button("Confirmar entrada" if ent else "Confirmar saída", type="primary")
    if ok_btn:
        if ent:
            ok, msg = db.registrar_entrada(uid, escolhido, int(qtd), val, obs)
        else:
            ok, msg = db.registrar_saida(uid, escolhido, int(qtd), obs)
        if not ok:
            st.warning(msg)
            return
        aviso(msg)
        st.rerun()


def _painel_produto(uid, pid):
    p = db.obter_produto(uid, pid)
    if not p:
        st.warning("Produto não encontrado.")
        return
    st.caption(f'{p["categoria"]}  ·  {moeda(float(p["preco"]))}')
    c1, c2, c3 = st.columns(3)
    c1.metric("Estoque", f'{p["quantidade"]} un.')
    c2.metric("Mínimo", f'{p["estoque_minimo"]} un.')
    c3.metric("Validade", fmt_data(p["validade"]) or "—")
    b1, b2 = st.columns(2)
    if b1.button("↓  Entrada", key="pn_ent"):
        abrir("mov", "entrada", pid)
    if b2.button("↑  Saída", key="pn_sai"):
        abrir("mov", "saida", pid)
    if st.button("Editar cadastro", key="pn_edit"):
        abrir("produto", pid)
    if st.button("Excluir produto", key="pn_del"):
        abrir("excluir", pid)


def _excluir(uid, pid):
    p = db.obter_produto(uid, pid)
    if not p:
        st.warning("Produto não encontrado.")
        return
    st.write(f'Excluir **{esc(p["nome"])}**?')
    st.caption("Só é possível para itens sem movimentações.")
    c1, c2 = st.columns(2)
    if c1.button("Cancelar", key="ex_cancel"):
        st.rerun()
    if c2.button("Excluir", type="primary", key="ex_ok"):
        ok, msg = db.excluir_produto(uid, pid)
        aviso(msg if ok else f"⚠️ {msg}")
        st.rerun()


def _form_senha(uid):
    with st.form("f_senha"):
        atual = st.text_input("Senha atual", type="password")
        nova = st.text_input("Nova senha", type="password")
        conf = st.text_input("Confirmar nova senha", type="password")
        salvar = st.form_submit_button("Salvar", type="primary")
    if salvar:
        if nova != conf:
            st.error("As senhas não coincidem.")
            return
        ok, msg = db.alterar_senha(uid, atual, nova)
        if not ok:
            st.error(msg)
            return
        aviso(msg)
        st.rerun()


def mostrar_dialogo(uid, dlg):
    """Abre o diálogo pedido. (st.dialog não permite diálogos aninhados,
    por isso as ações agendam o próximo diálogo via session_state.)"""
    tipo, *args = dlg
    if tipo == "produto":
        st.dialog("Editar produto" if args[0] else "Novo produto")(_form_produto)(uid, *args)
    elif tipo == "mov":
        titulo = "Registrar entrada" if args[0] == "entrada" else "Registrar saída"
        st.dialog(titulo)(_form_mov)(uid, *args)
    elif tipo == "painel":
        p = db.obter_produto(uid, args[0])
        st.dialog(p["nome"] if p else "Produto")(_painel_produto)(uid, *args)
    elif tipo == "excluir":
        st.dialog("Excluir produto")(_excluir)(uid, *args)
    elif tipo == "senha":
        st.dialog("Alterar senha")(_form_senha)(uid)


# ======================= COMPONENTES =======================
def barra_topo(placeholder, chave, botao):
    c1, c2 = st.columns([5, 1], vertical_alignment="center")
    busca = c1.text_input("Buscar", placeholder=f"⌕  {placeholder}", key=f"busca_{chave}",
                          label_visibility="collapsed")
    clicou = c2.button(botao, type="primary", key=f"top_{chave}")
    return busca, clicou


def card_produto(p, ctx, acoes):
    sit = situacao(p)
    with st.container(border=True):
        proporcao = [4, 1.5, 1, 3.3] if acoes else [5, 1.6, 1, 1.4]
        c_info, c_val, c_qtd, c_acao = st.columns(proporcao, vertical_alignment="center")

        badge = f'<span class="badge {sit[1]}">{esc(sit[0])}</span>' if sit else ""
        c_info.markdown(
            f'<div class="pnome">{esc(p["nome"]).upper()}{badge}</div>'
            f'<div class="psub">{esc(p["categoria"])}  ·  {moeda(float(p["preco"]))}</div>',
            unsafe_allow_html=True)

        vencido = bool(sit and sit[0] == "Vencido")
        c_val.markdown(f'<div class="pval{" venc" if vencido else ""}">▣  {fmt_data(p["validade"], True)}</div>',
                       unsafe_allow_html=True)

        baixo = p["quantidade"] <= p["estoque_minimo"]
        c_qtd.markdown(f'<div class="pqtd{" baixo" if baixo else ""}">{p["quantidade"]}</div>',
                       unsafe_allow_html=True)

        if acoes:
            b1, b2, b3 = c_acao.columns(3)
            if b1.button("Entrada", key=f"{ctx}_ent_{p['id']}"):
                abrir("mov", "entrada", p["id"])
            if b2.button("Saída", key=f"{ctx}_sai_{p['id']}"):
                abrir("mov", "saida", p["id"])
            if b3.button("Editar", key=f"{ctx}_edit_{p['id']}"):
                abrir("produto", p["id"])
        else:
            if c_acao.button("Abrir", key=f"{ctx}_abrir_{p['id']}"):
                abrir("painel", p["id"])


def lista_produtos(uid, busca, ctx, acoes, ordenar):
    prods = db.listar_produtos(uid, busca)
    if ordenar:
        prods.sort(key=lambda p: situacao(p) is None)  # alertas primeiro
    for p in prods:
        card_produto(p, ctx, acoes)
    if not prods:
        st.info("Nenhum produto encontrado. " +
                ("Tente outro termo." if busca else "Clique em “+ Novo” para cadastrar o primeiro item."))


# ======================= TELAS =======================
def tela_inicio(uid, u):
    busca, novo = barra_topo("Buscar produto...", "inicio", "+  Novo")
    if novo:
        abrir("produto", None)
    hora = datetime.now().hour
    saud = "Bom dia" if hora < 12 else "Boa tarde" if hora < 18 else "Boa noite"
    st.subheader(f'{saud}, {u["nome"].split()[0]}')
    st.caption("Itens com alerta aparecem primeiro. Clique em “Abrir” para movimentar.")
    lista_produtos(uid, busca, "inicio", acoes=False, ordenar=True)


def tela_produtos(uid, u):
    busca, novo = barra_topo("Buscar por nome ou categoria...", "produtos", "+  Novo")
    if novo:
        abrir("produto", None)
    st.subheader("Produtos")
    st.caption("Gerencie cadastro, entradas e saídas")
    lista_produtos(uid, busca, "prod", acoes=True, ordenar=False)


def tela_vendas(uid, u):
    busca, saida = barra_topo("Buscar movimentação...", "vendas", "↑  Saída")
    if saida:
        abrir("mov", "saida", None)
    st.subheader("Vendas e movimentações")
    st.caption("Histórico de entradas e saídas do seu estoque")
    movs = db.listar_movimentacoes(uid, busca)
    for m in movs:
        ent = m["tipo"] == "entrada"
        with st.container(border=True):
            c_ic, c_info, c_total, c_qtd = st.columns([0.6, 5, 1.6, 1.2], vertical_alignment="center")
            c_ic.markdown(f'<div class="mov {"ent" if ent else "sai"}">{"↓" if ent else "↑"}</div>',
                          unsafe_allow_html=True)
            det = ["Entrada" if ent else "Saída", m["data"].strftime("%d/%m/%Y  %H:%M")]
            if m["validade_lote"]:
                det.append(f"lote vence {fmt_data(m['validade_lote'])}")
            if m["observacao"]:
                det.append(m["observacao"])
            c_info.markdown(f'<div class="pnome">{esc(m["nome"]).upper()}</div>'
                            f'<div class="psub">{esc("  ·  ".join(det))}</div>',
                            unsafe_allow_html=True)
            if not ent and float(m["valor_unit"]):
                c_total.markdown(f'<div class="psub">{moeda(m["quantidade"] * float(m["valor_unit"]))}</div>',
                                 unsafe_allow_html=True)
            c_qtd.markdown(f'<div class="mov {"ent" if ent else "sai"}">{"+" if ent else "−"}{m["quantidade"]}</div>',
                           unsafe_allow_html=True)
    if not movs:
        st.info("Sem movimentações. Entradas e saídas registradas aparecem aqui.")


def tela_config(uid, u):
    st.subheader("Configurações")
    st.caption("Conta, alertas e conexão")

    with st.container(border=True):
        st.markdown("**Minha conta**")
        st.caption(f'{u["nome"]}  ·  @{u["usuario"]}')
        if st.button("Alterar senha", key="cfg_senha"):
            abrir("senha")

    baixos = db.itens_baixos(uid)
    with st.container(border=True):
        st.markdown(f":red[**Abaixo do estoque mínimo ({len(baixos)})**]")
        for p in baixos:
            c1, c2 = st.columns([4, 1])
            c1.write(p["nome"])
            c2.markdown(f':red[{p["quantidade"]} de {p["estoque_minimo"]} un.]')
        if not baixos:
            st.caption("Nenhum item — tudo certo.")

    vencendo = db.proximos_vencimento(uid)
    with st.container(border=True):
        st.markdown(f":orange[**Vencendo em até {db.DIAS_ALERTA_VALIDADE} dias ({len(vencendo)})**]")
        for p in vencendo:
            c1, c2 = st.columns([4, 1])
            c1.write(p["nome"])
            c2.markdown(":orange[Vencido]" if p["dias"] < 0
                        else f':orange[{fmt_data(p["validade"])}  ·  {p["dias"]}d]')
        if not vencendo:
            st.caption("Nenhum item — tudo certo.")

    with st.container(border=True):
        st.markdown("**Banco de dados**")
        st.caption(f'SQLite  ·  arquivo “{db.DB_NAME}”  ·  conectado')


TELAS = {PAGINAS[0]: tela_inicio, PAGINAS[1]: tela_produtos,
         PAGINAS[2]: tela_vendas, PAGINAS[3]: tela_config}


# ======================= PRINCIPAL =======================
def tela_principal(u):
    uid = u["id"]
    r = db.resumo(uid)

    with st.sidebar:
        st.markdown(
            f'<div style="display:flex;align-items:center;margin-bottom:12px">'
            f'<span class="avatar">{esc(iniciais(u["nome"]))}</span>'
            f'<div><div class="pnome">{esc(u["nome"].split()[0]).upper()}</div>'
            f'<div class="psub">@{esc(u["usuario"])}</div></div></div>',
            unsafe_allow_html=True)
        st.metric("PRODUTOS", r["produtos"])
        st.metric("ESTOQUE BAIXO", r["baixos"])
        st.metric("VENDIDO", moeda(r["vendido"]))
        st.divider()
        pagina = st.radio("Navegação", PAGINAS, key="pagina", label_visibility="collapsed")
        st.divider()
        if st.button("Sair da conta", key="sair"):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

    TELAS[pagina](uid, u)

    dlg = st.session_state.pop("_dlg", None)
    if dlg:
        mostrar_dialogo(uid, dlg)


def main():
    try:
        iniciar_banco()
    except Exception as e:
        st.error("Não foi possível abrir o banco de dados SQLite. Verifique se a pasta do app "
                 "permite gravação e recarregue a página.")
        st.code(str(e))
        st.stop()

    msg = st.session_state.pop("_toast", None)
    if msg:
        st.toast(msg)

    u = st.session_state.get("usuario")
    if not u:
        tela_login()
    else:
        try:
            tela_principal(u)
        except Exception as e:
            st.error(f"Erro ao acessar o banco de dados: {e}")


main()
