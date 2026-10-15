# Cantina — Streamlit + SQLite

O banco é um arquivo (`cantina.db`) criado automaticamente na primeira execução.
Não precisa de XAMPP, MySQL nem configuração.

## Rodar
```
pip install -r requirements.txt
streamlit run app.py
```

## Publicar na web
**Importante:** o SQLite grava num arquivo. Em hospedagens com disco temporário
(como o Streamlit Community Cloud), esse arquivo é **apagado** quando o app reinicia ou é
republicado — contas e estoque somem. Para os dados persistirem, hospede onde exista
disco persistente e aponte o banco para ele com a variável `SQLITE_PATH`:

- **Render / Railway / Fly.io:** crie um *Persistent Disk / Volume* (ex.: montado em `/data`),
  defina `SQLITE_PATH=/data/cantina.db` e use o comando de start:
  `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
- **VPS própria** (ou o próprio computador exposto na rede): basta rodar o comando acima;
  o arquivo `cantina.db` fica na pasta do app.

Para demonstração (trabalho da faculdade, por exemplo), o Streamlit Community Cloud funciona,
mas crie as contas/produtos de novo se o app reiniciar.

`app_desktop_tkinter.py` é a versão original (CustomTkinter), só como referência.
