"""Cantina — controle de estoque com login (CustomTkinter + MySQL)."""
import tkinter as tk
from tkinter import messagebox
from datetime import datetime, date
import customtkinter as ctk
import database as db

ctk.set_appearance_mode("dark")

# ---------------- paleta (layout de referência, refinado) ----------------
BG = "#0e1524"
SIDE = "#0b1120"
CARD = "#141d31"
CARD_HOVER = "#18233b"
LINE = "#222d45"
CHIP = "#1b2640"
TXT = "#eef2f8"
SUB = "#8a97b0"
FAINT = "#56627a"
BLUE = "#3b82f6"
BLUE_H = "#2f6fdb"
BLUE_SEL = "#172a52"
PURPLE, PURPLE_BG = "#8b8cf6", "#23244a"
TEAL, TEAL_BG = "#2dd4b0", "#123634"
ROSE, ROSE_BG = "#f2627a", "#3a1a26"
AMBER, AMBER_BG = "#f5b041", "#3a2d14"
F, FS = "Segoe UI", "Segoe UI Semibold"


def parse_data(txt):
    txt = txt.strip()
    return datetime.strptime(txt, "%d/%m/%Y").date() if txt else None


def fmt_data(d, curto=False):
    if not d:
        return "--/--/--" if curto else ""
    return d.strftime("%d/%m/%y" if curto else "%d/%m/%Y")


def moeda(v):
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def iniciais(nome):
    p = nome.split()
    return (p[0][0] + (p[-1][0] if len(p) > 1 else p[0][1:2])).upper()


def situacao(p):
    """(texto, cor, fundo) ou None se estiver tudo normal."""
    if p["validade"] and p["quantidade"] > 0:
        d = (p["validade"] - date.today()).days
        if d < 0:
            return "Vencido", ROSE, ROSE_BG
        if d <= db.DIAS_ALERTA_VALIDADE:
            return f"Vence em {d}d", AMBER, AMBER_BG
    if p["quantidade"] <= p["estoque_minimo"]:
        return "Estoque baixo", ROSE, ROSE_BG
    return None


# ========================================================================
#  APP
# ========================================================================
class App(ctk.CTk):
    def __init__(self):
        super().__init__(fg_color=BG)
        self.title("Cantina — Estoque")
        self.geometry("1120x720")
        self.minsize(960, 620)
        self.usuario = None
        self.tela_login()

    def limpar_janela(self):
        for w in self.winfo_children():
            w.destroy()

    # ===================== LOGIN / CADASTRO =====================
    def tela_login(self, modo="entrar"):
        self.limpar_janela()
        self.usuario = None
        fundo = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        fundo.pack(fill="both", expand=True)

        card = ctk.CTkFrame(fundo, fg_color=CARD, corner_radius=14, border_width=1,
                            border_color=LINE, width=400)
        card.place(relx=0.5, rely=0.5, anchor="center")
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(padx=38, pady=34)

        logo = ctk.CTkFrame(inner, fg_color="transparent")
        logo.pack(pady=(0, 18))
        ctk.CTkLabel(logo, text="C", width=46, height=46, corner_radius=12, fg_color=BLUE,
                     text_color="white", font=(FS, 22)).pack(side="left")
        ctk.CTkLabel(logo, text="  Cantina", font=(FS, 24), text_color=TXT).pack(side="left")

        entrar = modo == "entrar"
        ctk.CTkLabel(inner, text="Bem-vindo de volta" if entrar else "Criar sua conta",
                     font=(FS, 18), text_color=TXT).pack(anchor="w")
        ctk.CTkLabel(inner, text="Entre para acessar seu estoque" if entrar
                     else "Cada conta tem o próprio estoque e histórico",
                     font=(F, 12), text_color=SUB).pack(anchor="w", pady=(0, 18))

        def campo(rot, senha=False, dica=""):
            ctk.CTkLabel(inner, text=rot, font=(FS, 12), text_color=SUB, anchor="w").pack(fill="x")
            e = ctk.CTkEntry(inner, width=320, height=40, corner_radius=8, fg_color=BG,
                             border_color=LINE, text_color=TXT, placeholder_text=dica,
                             placeholder_text_color=FAINT, font=(F, 13), show="•" if senha else "")
            e.pack(pady=(4, 12))
            return e

        nome = None if entrar else campo("Nome completo", dica="Como você quer ser chamado")
        usuario = campo("Usuário", dica="ex.: maria")
        senha = campo("Senha", True, "••••••")
        conf = None if entrar else campo("Confirmar senha", True, "••••••")
        erro = ctk.CTkLabel(inner, text="", font=(F, 12), text_color=ROSE, height=16)
        erro.pack(anchor="w")

        def enviar(_=None):
            erro.configure(text="Aguarde...")
            self.update_idletasks()
            try:
                if not entrar:
                    if senha.get() != conf.get():
                        erro.configure(text="As senhas não coincidem")
                        return
                    ok, msg = db.registrar_usuario(nome.get(), usuario.get(), senha.get())
                    if not ok:
                        erro.configure(text=msg)
                        return
                u = db.autenticar(usuario.get(), senha.get())
            except Exception as e:
                erro.configure(text=f"Erro de conexão com o banco: {e}")
                return
            if not u:
                erro.configure(text="Usuário ou senha incorretos")
                return
            self.usuario = u
            # troca de tela fora do callback do botão (evita travar a janela)
            self.after(10, self._abrir_principal)

        ctk.CTkButton(inner, text="Entrar" if entrar else "Criar conta", height=42, corner_radius=8,
                      fg_color=BLUE, hover_color=BLUE_H, font=(FS, 14),
                      command=enviar).pack(fill="x", pady=(8, 14))
        rod = ctk.CTkFrame(inner, fg_color="transparent")
        rod.pack()
        ctk.CTkLabel(rod, text="Não tem conta?" if entrar else "Já tem conta?",
                     font=(F, 12), text_color=SUB).pack(side="left")
        link = ctk.CTkLabel(rod, text=" Criar registro" if entrar else " Entrar", font=(FS, 12),
                            text_color=BLUE, cursor="hand2")
        link.pack(side="left")
        link.bind("<Button-1>", lambda _: self.tela_login("registrar" if entrar else "entrar"))
        self.bind("<Return>", enviar)
        (nome or usuario).focus_set()

    # ===================== ESTRUTURA PRINCIPAL =====================
    def _abrir_principal(self):
        try:
            self.tela_principal()
        except Exception:
            import traceback
            detalhe = traceback.format_exc()
            with open("erro.log", "a", encoding="utf-8") as f:
                f.write(f"\n[{datetime.now()}]\n{detalhe}")
            messagebox.showerror("Erro ao abrir o sistema",
                                 "Ocorreu um erro. Detalhes salvos em erro.log.\n\n" + detalhe[-600:])
            self.tela_login()

    def tela_principal(self):
        self.unbind("<Return>")
        self.limpar_janela()
        self.uid = self.usuario["id"]
        self.nav = {}

        self.side = ctk.CTkFrame(self, fg_color=SIDE, corner_radius=0, width=250)
        self.side.pack(side="left", fill="y")
        self.side.pack_propagate(False)
        ctk.CTkFrame(self, fg_color=LINE, width=1, corner_radius=0).pack(side="left", fill="y")
        self.main = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        self.main.pack(side="left", fill="both", expand=True)

        # perfil
        topo = ctk.CTkFrame(self.side, fg_color="transparent")
        topo.pack(fill="x", padx=18, pady=(22, 16))
        ctk.CTkLabel(topo, text=iniciais(self.usuario["nome"]), width=44, height=44, corner_radius=22,
                     fg_color=BLUE, text_color="white", font=(FS, 15)).pack(side="left")
        txt = ctk.CTkFrame(topo, fg_color="transparent")
        txt.pack(side="left", padx=12)
        ctk.CTkLabel(txt, text=self.usuario["nome"].split()[0].upper(), font=(FS, 16),
                     text_color=TXT, anchor="w", height=20).pack(anchor="w")
        ctk.CTkLabel(txt, text=f'@{self.usuario["usuario"]}', font=(F, 11),
                     text_color=SUB, anchor="w", height=16).pack(anchor="w")

        # indicadores
        self.ind = {}
        for chave, glifo, titulo, cor, fundo in [("produtos", "▦", "PRODUTOS", PURPLE, PURPLE_BG),
                                                 ("baixos", "↓", "ESTOQUE BAIXO", TEAL, TEAL_BG),
                                                 ("vendido", "$", "VENDIDO", ROSE, ROSE_BG)]:
            f = ctk.CTkFrame(self.side, fg_color=CARD, corner_radius=12, border_width=1, border_color=LINE)
            f.pack(fill="x", padx=14, pady=5)
            ctk.CTkLabel(f, text=glifo, width=46, height=46, corner_radius=10, fg_color=fundo,
                         text_color=cor, font=(FS, 20)).pack(side="left", padx=12, pady=12)
            b = ctk.CTkFrame(f, fg_color="transparent")
            b.pack(side="left")
            ctk.CTkLabel(b, text=titulo, font=(FS, 10), text_color=SUB, anchor="w", height=14).pack(anchor="w")
            v = ctk.CTkLabel(b, text="0", font=(FS, 19), text_color=TXT, anchor="w", height=26)
            v.pack(anchor="w")
            self.ind[chave] = v

        ctk.CTkFrame(self.side, fg_color="transparent", height=14).pack()
        for chave, glifo, nome in [("inicio", "⌂", "INÍCIO"), ("produtos", "▢", "PRODUTOS"),
                                   ("vendas", "↗", "VENDAS"), ("config", "⚙", "CONFIGURAÇÕES")]:
            b = ctk.CTkButton(self.side, text=f"  {glifo}     {nome}", anchor="w", height=42,
                              corner_radius=8, fg_color="transparent", hover_color=CARD,
                              text_color=SUB, font=(FS, 12), command=lambda c=chave: self.ir(c))
            b.pack(fill="x", padx=12, pady=2)
            self.nav[chave] = b

        ctk.CTkButton(self.side, text="Sair da conta", height=36, corner_radius=8,
                      fg_color="transparent", border_width=1, border_color=LINE, hover_color=CARD,
                      text_color=SUB, font=(F, 12),
                      command=self.sair).pack(side="bottom", fill="x", padx=14, pady=18)
        self.ir("inicio")

    def sair(self):
        if messagebox.askyesno("Sair", "Deseja sair da conta?"):
            self.tela_login()

    def ir(self, chave):
        for c, b in self.nav.items():
            on = c == chave
            b.configure(fg_color=BLUE_SEL if on else "transparent", text_color="#93b8ff" if on else SUB)
        self.tela = {"inicio": self.tela_inicio, "produtos": self.tela_produtos,
                     "vendas": self.tela_vendas, "config": self.tela_config}[chave]
        self.recarregar()

    def recarregar(self):
        for w in self.main.winfo_children():
            w.destroy()
        r = db.resumo(self.uid)
        self.ind["produtos"].configure(text=str(r["produtos"]))
        self.ind["baixos"].configure(text=str(r["baixos"]))
        self.ind["vendido"].configure(text=moeda(r["vendido"]))
        self.wrap = ctk.CTkFrame(self.main, fg_color="transparent")
        self.wrap.pack(fill="both", expand=True, padx=28, pady=24)
        self.tela()

    # ===================== COMPONENTES =====================
    def topo(self, placeholder, cb, botao=None):
        bar = ctk.CTkFrame(self.wrap, fg_color="transparent")
        bar.pack(fill="x", pady=(0, 18))
        e = ctk.CTkEntry(bar, placeholder_text=f"⌕   {placeholder}", height=44, corner_radius=10,
                         fg_color=CARD, border_color=LINE, text_color=TXT,
                         placeholder_text_color=FAINT, font=(F, 13))
        e.pack(side="left", fill="x", expand=True)
        e.bind("<KeyRelease>", lambda _: cb(e.get()))
        if botao:
            ctk.CTkButton(bar, text=botao[0], width=120, height=44, corner_radius=10, fg_color=BLUE,
                          hover_color=BLUE_H, font=(FS, 13), command=botao[1]).pack(side="left", padx=(16, 0))

    def titulo(self, texto, sub=""):
        ctk.CTkLabel(self.wrap, text=texto, font=(FS, 15), text_color=TXT, anchor="w").pack(fill="x")
        if sub:
            ctk.CTkLabel(self.wrap, text=sub, font=(F, 12), text_color=SUB, anchor="w").pack(fill="x")
        ctk.CTkFrame(self.wrap, fg_color="transparent", height=8).pack()

    def rolavel(self):
        s = ctk.CTkScrollableFrame(self.wrap, fg_color="transparent", scrollbar_button_color=LINE,
                                   scrollbar_button_hover_color=FAINT)
        s.pack(fill="both", expand=True)
        return s

    def vazio(self, pai, titulo, texto):
        f = ctk.CTkFrame(pai, fg_color="transparent")
        f.pack(pady=70)
        ctk.CTkLabel(f, text=titulo, font=(FS, 15), text_color=TXT).pack()
        ctk.CTkLabel(f, text=texto, font=(F, 12), text_color=SUB).pack(pady=(4, 0))

    def chip(self, pai, texto, cor=TXT, fundo=CHIP, w=None, fonte=(FS, 13)):
        return ctk.CTkLabel(pai, text=texto, width=w or 0, height=40, corner_radius=8,
                            fg_color=fundo, text_color=cor, font=fonte)

    def card_produto(self, pai, p, acoes=False):
        sit = situacao(p)
        c = ctk.CTkFrame(pai, fg_color=CARD, corner_radius=12, border_width=1, border_color=LINE)
        c.pack(fill="x", pady=5)
        if sit:  # faixa lateral discreta de alerta
            ctk.CTkFrame(c, fg_color=sit[1], width=3, corner_radius=2).pack(side="left", fill="y", padx=(6, 0), pady=14)

        ctk.CTkLabel(c, text=iniciais(p["nome"]), width=50, height=50, corner_radius=10,
                     fg_color=CHIP, text_color="#a9b8d6", font=(FS, 15)).pack(side="left", padx=14, pady=12)
        info = ctk.CTkFrame(c, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(info, text=p["nome"].upper(), font=(FS, 16), text_color=TXT,
                     anchor="w", height=22).pack(anchor="w")
        linha = ctk.CTkFrame(info, fg_color="transparent")
        linha.pack(anchor="w")
        ctk.CTkLabel(linha, text=f'{p["categoria"]}  ·  {moeda(float(p["preco"]))}', font=(F, 12),
                     text_color=SUB, height=18).pack(side="left")
        if sit:
            ctk.CTkLabel(linha, text=f"  {sit[0]}  ", font=(FS, 10), height=18, corner_radius=9,
                         fg_color=sit[2], text_color=sit[1]).pack(side="left", padx=10)

        dir_ = ctk.CTkFrame(c, fg_color="transparent")
        dir_.pack(side="right", padx=14)
        if acoes:
            for txt, cor, fn in [("Entrada", TEAL, lambda: self.form_mov("entrada", p["id"])),
                                 ("Saída", ROSE, lambda: self.form_mov("saida", p["id"])),
                                 ("Editar", SUB, lambda: self.form_produto(p["id"]))]:
                ctk.CTkButton(dir_, text=txt, width=74, height=34, corner_radius=8, fg_color="transparent",
                              border_width=1, border_color=LINE, hover_color=CARD_HOVER, text_color=cor,
                              font=(FS, 12), command=fn).pack(side="left", padx=3)
            ctk.CTkFrame(dir_, fg_color="transparent", width=8).pack(side="left")
        cor_val = sit[1] if sit and sit[0].startswith("Venc") else "#93b8ff"
        self.chip(dir_, f"▣  {fmt_data(p['validade'], True)}", cor_val, "#111a2d", 118,
                  (F, 13)).pack(side="left", padx=6)
        baixo = p["quantidade"] <= p["estoque_minimo"]
        self.chip(dir_, str(p["quantidade"]), ROSE if baixo else TXT, CHIP, 84, (FS, 16)).pack(side="left")

        if not acoes:
            self._clicavel(c, lambda: self.painel_produto(p))

    def _clicavel(self, w, fn):
        def on(_): w.configure(fg_color=CARD_HOVER)
        def off(_): w.configure(fg_color=CARD)
        w.bind("<Leave>", off)

        def bind(x):
            x.bind("<Button-1>", lambda _e: fn(), add="+")
            x.bind("<Enter>", on, add="+")
            try:
                x.configure(cursor="hand2")
            except (tk.TclError, ValueError):
                pass
            for c in x.winfo_children():
                if isinstance(c, ctk.CTkBaseClass):
                    bind(c)
        w.after(20, lambda: bind(w))

    # ===================== TELAS =====================
    def _lista(self, acoes, ordenar):
        lista = self.rolavel()

        def carregar(txt=""):
            for w in lista.winfo_children():
                w.destroy()
            prods = db.listar_produtos(self.uid, txt)
            if ordenar:
                prods.sort(key=lambda p: situacao(p) is None)
            for p in prods:
                self.card_produto(lista, p, acoes)
            if not prods:
                self.vazio(lista, "Nenhum produto encontrado",
                           "Tente outro termo." if txt else "Clique em “+ Novo” para cadastrar o primeiro item.")
        return carregar

    def tela_inicio(self):
        carregar = None
        self.topo("Buscar produto...", lambda t: carregar(t), ("+  Novo", lambda: self.form_produto(None)))
        hora = datetime.now().hour
        saud = "Bom dia" if hora < 12 else "Boa tarde" if hora < 18 else "Boa noite"
        self.titulo(f'{saud}, {self.usuario["nome"].split()[0]}',
                    "Itens com alerta aparecem primeiro. Clique em um produto para movimentar.")
        carregar = self._lista(False, True)
        carregar()

    def tela_produtos(self):
        carregar = None
        self.topo("Buscar por nome ou categoria...", lambda t: carregar(t),
                  ("+  Novo", lambda: self.form_produto(None)))
        self.titulo("Produtos", "Gerencie cadastro, entradas e saídas")
        carregar = self._lista(True, False)
        carregar()

    def tela_vendas(self):
        carregar = None
        self.topo("Buscar movimentação...", lambda t: carregar(t),
                  ("↑  Saída", lambda: self.form_mov("saida", None)))
        self.titulo("Vendas e movimentações", "Histórico de entradas e saídas do seu estoque")
        lista = self.rolavel()

        def carregar(txt=""):
            for w in lista.winfo_children():
                w.destroy()
            movs = db.listar_movimentacoes(self.uid, txt)
            for m in movs:
                ent = m["tipo"] == "entrada"
                c = ctk.CTkFrame(lista, fg_color=CARD, corner_radius=12, border_width=1, border_color=LINE)
                c.pack(fill="x", pady=4)
                ctk.CTkLabel(c, text="↓" if ent else "↑", width=42, height=42, corner_radius=10,
                             fg_color=TEAL_BG if ent else ROSE_BG, text_color=TEAL if ent else ROSE,
                             font=(FS, 18)).pack(side="left", padx=14, pady=10)
                info = ctk.CTkFrame(c, fg_color="transparent")
                info.pack(side="left", fill="x", expand=True)
                ctk.CTkLabel(info, text=m["nome"].upper(), font=(FS, 14), text_color=TXT,
                             anchor="w", height=20).pack(anchor="w")
                det = [("Entrada" if ent else "Saída"), m["data"].strftime("%d/%m/%Y  %H:%M")]
                if m["validade_lote"]:
                    det.append(f"lote vence {fmt_data(m['validade_lote'])}")
                if m["observacao"]:
                    det.append(m["observacao"])
                ctk.CTkLabel(info, text="  ·  ".join(det), font=(F, 11), text_color=SUB,
                             anchor="w", height=16).pack(anchor="w")
                if not ent and float(m["valor_unit"]):
                    ctk.CTkLabel(c, text=moeda(m["quantidade"] * float(m["valor_unit"])), font=(F, 12),
                                 text_color=SUB).pack(side="right", padx=(0, 14))
                self.chip(c, ("+" if ent else "−") + str(m["quantidade"]), TEAL if ent else ROSE,
                          CHIP, 74, (FS, 15)).pack(side="right", padx=14)
            if not movs:
                self.vazio(lista, "Sem movimentações", "Entradas e saídas registradas aparecem aqui.")
        carregar()

    def tela_config(self):
        self.titulo("Configurações", "Conta, alertas e conexão")
        s = self.rolavel()

        def bloco(titulo, cor=TXT):
            b = ctk.CTkFrame(s, fg_color=CARD, corner_radius=12, border_width=1, border_color=LINE)
            b.pack(fill="x", pady=6)
            ctk.CTkLabel(b, text=titulo, font=(FS, 14), text_color=cor, anchor="w").pack(fill="x", padx=20, pady=(16, 8))
            return b

        conta = bloco("Minha conta")
        ctk.CTkLabel(conta, text=f'{self.usuario["nome"]}  ·  @{self.usuario["usuario"]}', font=(F, 12),
                     text_color=SUB, anchor="w").pack(fill="x", padx=20)
        ctk.CTkButton(conta, text="Alterar senha", width=140, height=34, corner_radius=8, fg_color="transparent",
                      border_width=1, border_color=LINE, hover_color=CARD_HOVER, text_color=TXT,
                      font=(F, 12), command=self.form_senha).pack(anchor="w", padx=20, pady=(10, 16))

        for titulo, cor, itens, fmt in [
                ("Abaixo do estoque mínimo", ROSE, db.itens_baixos(self.uid),
                 lambda p: f'{p["quantidade"]} de {p["estoque_minimo"]} un.'),
                (f"Vencendo em até {db.DIAS_ALERTA_VALIDADE} dias", AMBER, db.proximos_vencimento(self.uid),
                 lambda p: "Vencido" if p["dias"] < 0 else f'{fmt_data(p["validade"])}  ·  {p["dias"]}d')]:
            b = bloco(f"{titulo}  ({len(itens)})", cor)
            for p in itens:
                l = ctk.CTkFrame(b, fg_color=CHIP, corner_radius=8)
                l.pack(fill="x", padx=16, pady=3)
                ctk.CTkLabel(l, text=p["nome"], font=(F, 13), text_color=TXT).pack(side="left", padx=12, pady=9)
                ctk.CTkLabel(l, text=fmt(p), font=(FS, 12), text_color=cor).pack(side="right", padx=12)
            if not itens:
                ctk.CTkLabel(b, text="Nenhum item — tudo certo.", font=(F, 12), text_color=SUB,
                             anchor="w").pack(fill="x", padx=20)
            ctk.CTkFrame(b, fg_color="transparent", height=12).pack()

        con = bloco("Banco de dados")
        ctk.CTkLabel(con, text=f'MySQL  ·  {db.CONFIG["host"]}:{db.CONFIG["port"]}  ·  banco “{db.DB_NAME}”  ·  conectado',
                     font=(F, 12), text_color=SUB, anchor="w").pack(fill="x", padx=20, pady=(0, 16))

    # ===================== MODAIS =====================
    def _modal(self, titulo, sub=""):
        w = ctk.CTkToplevel(self, fg_color=CARD)
        w.title(titulo)
        w.resizable(False, False)
        w.transient(self)
        w.after(120, w.grab_set)
        tk.Toplevel.configure(w, padx=28, pady=24)
        ctk.CTkLabel(w, text=titulo, font=(FS, 18), text_color=TXT, anchor="w").pack(fill="x")
        if sub:
            ctk.CTkLabel(w, text=sub, font=(F, 12), text_color=SUB, anchor="w").pack(fill="x")
        ctk.CTkFrame(w, fg_color="transparent", height=14).pack()
        return w

    def _campo(self, w, rot, valor="", dica="", senha=False):
        ctk.CTkLabel(w, text=rot, font=(FS, 12), text_color=SUB, anchor="w").pack(fill="x")
        e = ctk.CTkEntry(w, width=340, height=38, corner_radius=8, fg_color=BG, border_color=LINE,
                         text_color=TXT, placeholder_text=dica, placeholder_text_color=FAINT,
                         font=(F, 13), show="•" if senha else "")
        if valor not in ("", None):
            e.insert(0, str(valor))
        e.pack(pady=(4, 12))
        return e

    def _botoes(self, w, texto, cmd, cor=BLUE, hover=BLUE_H):
        b = ctk.CTkFrame(w, fg_color="transparent")
        b.pack(fill="x", pady=(6, 0))
        ctk.CTkButton(b, text=texto, command=cmd, height=38, corner_radius=8, fg_color=cor,
                      hover_color=hover, font=(FS, 13)).pack(side="right")
        ctk.CTkButton(b, text="Cancelar", command=w.destroy, height=38, corner_radius=8, fg_color="transparent",
                      border_width=1, border_color=LINE, hover_color=CARD_HOVER, text_color=TXT,
                      font=(F, 13)).pack(side="right", padx=8)

    def painel_produto(self, p):
        w = self._modal(p["nome"], f'{p["categoria"]}  ·  {moeda(float(p["preco"]))}')
        g = ctk.CTkFrame(w, fg_color=BG, corner_radius=10, border_width=1, border_color=LINE)
        g.pack(fill="x", pady=(0, 16))
        g.grid_columnconfigure((0, 1, 2), weight=1, uniform="g")
        for i, (rot, val) in enumerate([("Estoque", f'{p["quantidade"]} un.'),
                                        ("Mínimo", f'{p["estoque_minimo"]} un.'),
                                        ("Validade", fmt_data(p["validade"]) or "—")]):
            cel = ctk.CTkFrame(g, fg_color="transparent")
            cel.grid(row=0, column=i, sticky="w", padx=14, pady=12)
            ctk.CTkLabel(cel, text=rot, font=(F, 11), text_color=SUB, height=14).pack(anchor="w")
            ctk.CTkLabel(cel, text=val, font=(FS, 14), text_color=TXT).pack(anchor="w")

        def acao(fn):
            w.destroy()
            fn()

        linha = ctk.CTkFrame(w, fg_color="transparent")
        linha.pack(fill="x")
        linha.grid_columnconfigure((0, 1), weight=1, uniform="b")
        ctk.CTkButton(linha, text="↓  Entrada", height=40, corner_radius=8, fg_color=TEAL_BG, hover_color="#164441",
                      text_color=TEAL, font=(FS, 13),
                      command=lambda: acao(lambda: self.form_mov("entrada", p["id"]))).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ctk.CTkButton(linha, text="↑  Saída", height=40, corner_radius=8, fg_color=ROSE_BG, hover_color="#47202e",
                      text_color=ROSE, font=(FS, 13),
                      command=lambda: acao(lambda: self.form_mov("saida", p["id"]))).grid(row=0, column=1, sticky="ew", padx=(4, 0))
        ctk.CTkButton(w, text="Editar cadastro", height=38, corner_radius=8, fg_color="transparent", border_width=1,
                      border_color=LINE, hover_color=CARD_HOVER, text_color=TXT, font=(F, 13),
                      command=lambda: acao(lambda: self.form_produto(p["id"]))).pack(fill="x", pady=(8, 0))
        ctk.CTkButton(w, text="Excluir produto", height=30, fg_color="transparent", hover_color=ROSE_BG,
                      text_color=ROSE, font=(F, 12),
                      command=lambda: acao(lambda: self.excluir(p))).pack(pady=(10, 0))

    def excluir(self, p):
        if messagebox.askyesno("Excluir", f'Excluir "{p["nome"]}"?\nSó é possível para itens sem movimentações.'):
            ok, msg = db.excluir_produto(self.uid, p["id"])
            (messagebox.showinfo if ok else messagebox.showwarning)("Excluir", msg)
            self.recarregar()

    def form_produto(self, pid):
        p = db.obter_produto(self.uid, pid) if pid else None
        w = self._modal("Editar produto" if p else "Novo produto",
                        "Atualize o cadastro" if p else "O estoque começa em zero — use “Entrada” depois.")
        nome = self._campo(w, "Nome", p["nome"] if p else "", "Ex.: Suco de laranja")
        cat = self._campo(w, "Categoria", p["categoria"] if p else "", "Ex.: Bebidas")
        preco = self._campo(w, "Preço de venda (R$)", f'{float(p["preco"]):.2f}'.replace(".", ",") if p else "", "0,00")
        mini = self._campo(w, "Estoque mínimo", p["estoque_minimo"] if p else "", "Quantidade para alerta")
        val = self._campo(w, "Validade", fmt_data(p["validade"]) if p else "", "dd/mm/aaaa (opcional)")

        def salvar():
            n, c = nome.get().strip(), cat.get().strip()
            if not n or not c:
                messagebox.showerror("Dados inválidos", "Nome e categoria são obrigatórios.", parent=w)
                return
            try:
                m = int(mini.get() or 0)
                pr = float((preco.get() or "0").replace(",", "."))
                v = parse_data(val.get())
                if m < 0 or pr < 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Dados inválidos", "Verifique números e data (dd/mm/aaaa).", parent=w)
                return
            if p:
                db.editar_produto(self.uid, pid, n, c, m, v, pr)
            else:
                db.cadastrar_produto(self.uid, n, c, m, v, pr)
            w.destroy()
            self.recarregar()

        self._botoes(w, "Salvar" if p else "Cadastrar", salvar)

    def form_mov(self, tipo, pid):
        produtos = db.listar_produtos(self.uid)
        if not produtos:
            messagebox.showinfo("Sem produtos", "Cadastre um produto primeiro.")
            return
        ent = tipo == "entrada"
        w = self._modal("Registrar entrada" if ent else "Registrar saída",
                        "Recebimento de mercadoria (novo lote)" if ent else "Venda ou baixa de estoque")
        opcoes = [f'{p["id"]} · {p["nome"]} — {p["quantidade"]} un.' for p in produtos]
        ctk.CTkLabel(w, text="Produto", font=(FS, 12), text_color=SUB, anchor="w").pack(fill="x")
        cb = ctk.CTkComboBox(w, values=opcoes, width=340, height=38, corner_radius=8, state="readonly",
                             fg_color=BG, border_color=LINE, button_color=LINE, button_hover_color=FAINT,
                             dropdown_fg_color=CARD, dropdown_hover_color=CARD_HOVER, font=(F, 13))
        cb.set(next((o for o, p in zip(opcoes, produtos) if p["id"] == pid), opcoes[0]))
        cb.pack(pady=(4, 12))
        qtd = self._campo(w, "Quantidade", "", "Unidades")
        val = self._campo(w, "Validade do lote", "", "dd/mm/aaaa (opcional)") if ent else None
        obs = self._campo(w, "Observação", "", "Opcional")

        def salvar():
            try:
                prod_id = int(cb.get().split(" · ")[0])
                q = int(qtd.get())
                v = parse_data(val.get()) if ent else None
            except ValueError:
                messagebox.showerror("Dados inválidos", "Quantidade inteira e data dd/mm/aaaa.", parent=w)
                return
            ok, msg = (db.registrar_entrada(self.uid, prod_id, q, v, obs.get()) if ent
                       else db.registrar_saida(self.uid, prod_id, q, obs.get()))
            if not ok:
                messagebox.showwarning("Não foi possível registrar", msg, parent=w)
                return
            w.destroy()
            self.recarregar()

        self._botoes(w, "Confirmar entrada" if ent else "Confirmar saída", salvar,
                     "#14876f" if ent else "#c94660", "#11735f" if ent else "#b13d55")

    def form_senha(self):
        w = self._modal("Alterar senha")
        atual = self._campo(w, "Senha atual", senha=True)
        nova = self._campo(w, "Nova senha", senha=True)
        conf = self._campo(w, "Confirmar nova senha", senha=True)

        def salvar():
            if nova.get() != conf.get():
                messagebox.showerror("Erro", "As senhas não coincidem.", parent=w)
                return
            ok, msg = db.alterar_senha(self.uid, atual.get(), nova.get())
            (messagebox.showinfo if ok else messagebox.showerror)("Senha", msg, parent=w)
            if ok:
                w.destroy()

        self._botoes(w, "Salvar", salvar)


if __name__ == "__main__":
    try:
        db.criar_banco()
    except Exception as e:
        tk.Tk().withdraw()
        messagebox.showerror("Sem conexão com o banco",
                             "Não foi possível conectar ao MySQL.\n"
                             f"Inicie o MySQL no painel do XAMPP e tente novamente.\n\n{e}")
        raise SystemExit(1)
    App().mainloop()
