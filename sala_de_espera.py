import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import messagebox

# integração com backend
from control import ControllerSala, ControllerUsuario
from requesicao import requestBD
import enviar_texto

# Cria a janela principal
app = ttk.Window(themename="cyborg")
app.title("Lobby Multiplayer")
app.geometry("1200x780")

# controllers
ctrl_sala = ControllerSala()
ctrl_usuario = ControllerUsuario()

# estado local
current_sala_id = None
# polling
POLL_INTERVAL_MS = 3000  # 3 segundos
polling_job = None
auto_refresh_enabled = False

def _parse_response_rows(resp):
    """Tenta extrair uma lista de linhas (cada linha tuple/dict) da resposta do servidor.
    Aceita formatos comuns: list of dicts, list of tuples, {'rows': [...]}, {'result': [...]}
    Retorna lista de rows (cada row como dict or tuple) ou [] em falha."""
    if resp is None:
        return []
    # se já for lista, assume que é a lista de linhas
    if isinstance(resp, list):
        return resp
    # dicionário contendo chaves comuns
    if isinstance(resp, dict):
        for key in ('rows', 'result', 'data', 'items'):
            if key in resp and isinstance(resp[key], list):
                return resp[key]
        # em alguns backends a própria dict é uma linha
        return [resp]
    # caso simples (string/number)
    return [resp]

def _extract_inserted_id(resp):
    """Tenta extrair um id inserido de uma resposta do servidor."""
    if resp is None:
        return None
    if isinstance(resp, dict):
        for key in ('lastrowid', 'last_insert_id', 'insertId', 'inserted_id', 'id'):
            if key in resp:
                try:
                    return int(resp[key])
                except Exception:
                    return resp[key]
    if isinstance(resp, (int, str)):
        try:
            return int(resp)
        except Exception:
            return resp
    return None


def open_waiting_room(master, sala_id, is_host=False, username=None):
    """Abre uma janela de Sala de Espera (Toplevel) para a sala_id fornecida.
    is_host indica se o usuário que abriu a sala é o anfitrião e pode iniciar a partida.
    username é o nome exibido na lista/chat."""
    top = tk.Toplevel(master)
    top.title(f"Sala {sala_id} - Sala de Espera")
    top.geometry("1000x700")

    # Lista de jogadores (esquerda)
    players_frame = ttk.Labelframe(top, text="JOGADORES", padding=10)
    players_frame.pack(side=LEFT, fill=Y)

    players_list = tk.Listbox(players_frame, height=20)
    players_list.pack(fill=Y, expand=YES)

    # Chat (direita)
    chat_frame = ttk.Labelframe(top, text="CHAT", padding=10)
    chat_frame.pack(side=LEFT, fill=BOTH, expand=YES, padx=10)
    chat_box = tk.Text(chat_frame, height=20, state=NORMAL, wrap=WORD)
    chat_box.config(state=DISABLED)
    chat_box.pack(fill=BOTH, expand=YES)

    # Entrada de mensagem
    entry_frame = ttk.Frame(chat_frame)
    entry_frame.pack(fill=X, pady=5)

    msg_entry = ttk.Entry(entry_frame)
    msg_entry.pack(side=LEFT, fill=X, expand=YES, padx=5)

    # track last message timestamp/id to avoid reprinting duplicates
    last_chat_ts = {'value': None}

    def atualizar_chat():
        try:
            # busca mensagens da sala em ordem cronológica
            resp = ctrl_sala.listar_chat(sala_id, limit=200)
            rows = _parse_response_rows(resp)
            # se não houver rows, nada a fazer
            if not rows:
                return
            # build display from rows, but avoid duplicating já mostradas
            chat_box.config(state=NORMAL)
            for row in rows:
                usuario = None
                mensagem = None
                ts = None
                if isinstance(row, dict):
                    usuario = row.get('usuario') or row.get('nome') or row.get('Usuario')
                    mensagem = row.get('mensagem') or row.get('message') or row.get('msg')
                    ts = row.get('ts') or row.get('timestamp')
                elif isinstance(row, (list, tuple)):
                    # assume order usuario, mensagem, ts
                    if len(row) >= 3:
                        usuario, mensagem, ts = row[0], row[1], row[2]
                    elif len(row) == 2:
                        usuario, mensagem = row[0], row[1]
                if usuario is None:
                    usuario = 'Anônimo'
                if mensagem is None:
                    mensagem = str(row)
                # simple duplication guard: if ts exists and <= last_chat_ts, skip
                try:
                    if ts is not None and last_chat_ts['value'] is not None:
                        if isinstance(ts, str):
                            # try to compare lexicographically if ISO format
                            if ts <= last_chat_ts['value']:
                                continue
                        else:
                            if ts <= last_chat_ts['value']:
                                continue
                except Exception:
                    pass
                chat_box.insert(END, f"{usuario}: {mensagem}\n")
                # update last_chat_ts
                if ts is not None:
                    last_chat_ts['value'] = ts
            chat_box.config(state=DISABLED)
            # autoscroll to end
            chat_box.see(END)
        except Exception as e:
            # non-fatal: just skip
            pass

    def enviar_msg():
        txt = msg_entry.get().strip()
        if not txt:
            return
        usuario = username or 'Anon'
        # escape single quotes for SQL
        try:
            ctrl_sala.inserir_chat(sala_id, usuario, txt)
        except Exception:
            pass
        # show immediately locally
        chat_box.config(state=NORMAL)
        chat_box.insert(END, f"{usuario}: {txt}\n")
        chat_box.config(state=DISABLED)
        chat_box.see(END)
        msg_entry.delete(0, END)

    send_btn = ttk.Button(entry_frame, text="Enviar", bootstyle=SUCCESS, command=enviar_msg)
    send_btn.pack(side=LEFT)

    # Código da sala e controles superiores
    top_code_frame = ttk.Frame(top, padding=6)
    top_code_frame.pack(fill=X)

    code_label = ttk.Label(top_code_frame, text=f"CÓDIGO: {sala_id}", font=("Segoe UI", 14))
    code_label.pack(side=LEFT, padx=6)

    # Host controls
    def iniciar_partida():
        try:
            sql = f"UPDATE Sala SET started = 1 WHERE id = {sala_id};"
            requestBD(sql)
            messagebox.showinfo("Partida", "Partida iniciada pelo anfitrião.", parent=top)
            # abrir imediatamente a tela de escrever frase para o host
            try:
                print('[DEBUG] sala_de_espera: host opening WritePhraseScreen')
                top.withdraw()
                win = tk.Toplevel(top)
                # keep a reference on the Toplevel to avoid GC of the screen instance
                win._writephrase_screen = enviar_texto.WritePhraseScreen(win, duration=30, parent_to_restore=top)
                try:
                    win.focus_force()
                except Exception:
                    pass
            except Exception:
                # se não conseguir abrir embutido, apenas continuar (os clientes serão notificados via polling)
                pass
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível iniciar a partida.\n\n{e}", parent=top)

    if is_host:
        start_btn = ttk.Button(top_code_frame, text="Iniciar Partida", bootstyle=PRIMARY, command=iniciar_partida)
        start_btn.pack(side=LEFT, padx=6)

    # Nota: O botão "Escrever Frase" foi removido. A tela de escrever frase
    # será aberta automaticamente quando a partida for iniciada (campo
    # Sala.started = 1) — os clientes detectam isso pelo polling abaixo.

    sair_btn = ttk.Button(top_code_frame, text="Sair", bootstyle=DANGER, command=top.destroy)
    sair_btn.pack(side=RIGHT, padx=6)

    # Funções de atualização
    def atualizar():
        players_list.delete(0, END)
        try:
            resp = ctrl_sala.listar_jogadores(sala_id)
            rows = _parse_response_rows(resp)
            if not rows:
                return
            for row in rows:
                nome = None
                if isinstance(row, dict):
                    nome = row.get('nome') or row.get('Nome') or row.get('username')
                elif isinstance(row, (list, tuple)):
                    if len(row) >= 2:
                        nome = row[1]
                    elif len(row) == 1:
                        nome = row[0]
                if nome is None:
                    nome = str(row)
                players_list.insert(END, nome)
        except Exception as e:
            messagebox.showwarning("Aviso", f"Não foi possível atualizar lista de usuários.\n\n{e}", parent=top)

    # Auto-refresh simples
    polling = {'job': None}
    # garante que só disparemos a transição uma vez por cliente
    started_handled = {'value': False}

    def _poll_step():
        atualizar()
        atualizar_chat()
        # verifica se a sala foi marcada como 'started' no servidor
        try:
            resp = ctrl_sala.listar_sala(sala_id)
            # DEBUG: log raw response from listar_sala
            try:
                print(f"[DEBUG] listar_sala({sala_id}) raw: {resp}")
            except Exception:
                pass
            rows = _parse_response_rows(resp)
            if rows and not started_handled['value']:
                first = rows[0]
                started_val = None
                if isinstance(first, dict):
                    for k in ('started', 'Started', 'is_started'):
                        if k in first:
                            started_val = first.get(k)
                            break
                elif isinstance(first, (list, tuple)):
                    # procura um valor 1/True além do id (tenta qualquer campo)
                    for v in first[1:]:
                        if v in (1, '1', True, 'true', 'True'):
                            started_val = 1
                            break
                try:
                    print(f"[DEBUG] detected started_val={started_val}")
                    if started_val in (1, '1', True, 'true', 'True'):
                        started_handled['value'] = True
                        # abre tela de escrever frase (cliente)
                        try:
                            print('[DEBUG] sala_de_espera: client opening WritePhraseScreen due to started flag')
                            top.withdraw()
                            win = tk.Toplevel(top)
                            win._writephrase_screen = enviar_texto.WritePhraseScreen(win, duration=30, parent_to_restore=top)
                            try:
                                win.focus_force()
                            except Exception:
                                pass
                        except Exception:
                            # se não conseguir abrir, apenas avisar; a janela principal continua
                            try:
                                messagebox.showinfo("Partida", "A partida começou. Abra a tela de escrever frase.", parent=top)
                            except Exception:
                                pass
                except Exception:
                    pass

        except Exception:
            pass

        polling['job'] = top.after(3000, _poll_step)

    def start_poll():
        if polling['job'] is None:
            polling['job'] = top.after(0, _poll_step)

    def stop_poll():
        if polling['job'] is not None:
            try:
                top.after_cancel(polling['job'])
            except Exception:
                pass
            polling['job'] = None

    # start auto-refresh by default
    start_poll()

    # preenche inicialmente
    atualizar()

    def on_close():
        stop_poll()
        try:
            top.destroy()
        except Exception:
            pass

    top.protocol("WM_DELETE_WINDOW", on_close)

    return top

# -------------------------
# Lista de jogadores (esquerda)
# -------------------------
main_frame = ttk.Frame(app, padding=10)
main_frame.pack(fill=BOTH, expand=YES)

players_frame = ttk.Labelframe(main_frame, text="JOGADORES", padding=10)
players_frame.pack(side=LEFT, fill=Y)

players_list = tk.Listbox(players_frame, height=15)
players_list.pack(fill=Y, expand=YES)

def atualizar_lista_usuarios():
    """Busca usuários reais da sala atual e atualiza a Listbox."""
    players_list.delete(0, tk.END)
    global current_sala_id
    try:
        if not current_sala_id:
            return
        resp = ctrl_sala.listar_jogadores(current_sala_id)
        rows = _parse_response_rows(resp)
        if not rows:
            return
        for row in rows:
            nome = None
            if isinstance(row, dict):
                # tente campos comuns
                nome = row.get('nome') or row.get('Nome') or row.get('username') or row.get('nome_usuario')
            elif isinstance(row, (list, tuple)):
                if len(row) >= 2:
                    nome = row[1]
                elif len(row) == 1:
                    nome = row[0]
            if nome is None:
                nome = str(row)
            players_list.insert(tk.END, nome)
    except Exception as e:
        messagebox.showwarning("Aviso", f"Não foi possível atualizar lista de usuários.\n\n{e}")

def _polling_step():
    global polling_job
    if current_sala_id:
        atualizar_lista_usuarios()
    # re-agenda se auto_refresh_enabled
    if auto_refresh_enabled:
        polling_job = app.after(POLL_INTERVAL_MS, _polling_step)

def start_auto_refresh():
    global auto_refresh_enabled, polling_job
    if auto_refresh_enabled:
        return
    auto_refresh_enabled = True
    polling_job = app.after(0, _polling_step)

def stop_auto_refresh():
    global auto_refresh_enabled, polling_job
    auto_refresh_enabled = False
    if polling_job is not None:
        try:
            app.after_cancel(polling_job)
        except Exception:
            pass
        polling_job = None

# -------------------------
# Chat (direita)
# -------------------------
chat_frame = ttk.Labelframe(main_frame, text="CHAT", padding=10)
chat_frame.pack(side=LEFT, fill=BOTH, expand=YES, padx=10)

chat_box = tk.Text(chat_frame, height=15, state=NORMAL, wrap=WORD)
chat_box.insert(END, "USER01: Olá\n")
chat_box.insert(END, "USER02: Oi\n")
chat_box.config(state=DISABLED)
chat_box.pack(fill=BOTH, expand=YES)

# Entrada de mensagem
entry_frame = ttk.Frame(chat_frame)
entry_frame.pack(fill=X, pady=5)

msg_entry = ttk.Entry(entry_frame)
msg_entry.pack(side=LEFT, fill=X, expand=YES, padx=5)

send_btn = ttk.Button(entry_frame, text="Enviar", bootstyle=SUCCESS)
send_btn.pack(side=LEFT)

# -------------------------
# Botões inferiores
# -------------------------
buttons_frame = ttk.Frame(app, padding=10)
buttons_frame.pack(fill=X)

exit_btn = ttk.Button(buttons_frame, text="SAIR", bootstyle=DANGER, command=app.destroy)
exit_btn.pack(side=LEFT, padx=5)

micar_btn = ttk.Button(buttons_frame, text="Iniciar", bootstyle=WARNING)
micar_btn.pack(side=LEFT, padx=5)

# Criar sala e entrar por código
def criar_sala():
    global current_sala_id
    try:
        resp = ctrl_sala.inserir_sala()
        # tenta extrair id
        sala_id = None
        if isinstance(resp, dict):
            for key in ('lastrowid', 'id', 'inserted_id'):
                if key in resp:
                    sala_id = resp[key]
                    break
        elif isinstance(resp, (int, str)):
            try:
                sala_id = int(resp)
            except Exception:
                sala_id = None
        # se não obteve id, tenta buscar a última sala criada
        if sala_id is None:
            # consulta última sala
            q = "SELECT id FROM Sala ORDER BY id DESC LIMIT 1;"
            r2 = requestBD(q)
            if isinstance(r2, list) and len(r2) > 0:
                first = r2[0]
                if isinstance(first, (list, tuple)):
                    sala_id = first[0]
                elif isinstance(first, dict):
                    sala_id = first.get('id')
        if sala_id:
            current_sala_id = int(sala_id)
            code_var.set(str(current_sala_id))
            messagebox.showinfo("Sala criada", f"Sala criada com id: {current_sala_id}")
            atualizar_lista_usuarios()
        else:
            messagebox.showwarning("Aviso", "Sala criada, mas não foi possível obter o id.")
    except Exception as e:
        messagebox.showerror("Erro", f"Não foi possível criar sala.\n\n{e}")

def entrar_por_codigo():
    global current_sala_id
    # Abre dialog para inserir código e nome de usuário
    dlg = tk.Toplevel(app)
    dlg.title("Entrar na sala")
    dlg.geometry("360x180")
    dlg.resizable(False, False)

    tk.Label(dlg, text="Código da sala:").pack(pady=(12, 0))
    entry_codigo = ttk.Entry(dlg)
    entry_codigo.pack(pady=6)

    tk.Label(dlg, text="Seu nome:").pack(pady=(6, 0))
    entry_nome = ttk.Entry(dlg)
    entry_nome.pack(pady=6)

    def _confirmar():
        codigo = entry_codigo.get().strip()
        nome = entry_nome.get().strip()
        if not codigo or not nome:
            messagebox.showwarning("Aviso", "Preencha código e nome.", parent=dlg)
            return
        try:
            codigo_int = int(codigo)
        except Exception:
            messagebox.showwarning("Aviso", "Código inválido.", parent=dlg)
            return
        try:
            # cria usuário
            r = ctrl_usuario.inserir_usuario(nome, "")
            # associa usuário à sala via update usando última id do usuário inserido
            # tenta obter id inserido
            usuario_id = None
            if isinstance(r, dict):
                for key in ('lastrowid', 'id', 'inserted_id'):
                    if key in r:
                        usuario_id = r[key]
                        break
            # se não obteve, tenta buscar último usuário
            if usuario_id is None:
                q = "SELECT id FROM Usuario ORDER BY id DESC LIMIT 1;"
                rr = requestBD(q)
                if isinstance(rr, list) and len(rr) > 0:
                    first = rr[0]
                    if isinstance(first, (list, tuple)):
                        usuario_id = first[0]
                    elif isinstance(first, dict):
                        usuario_id = first.get('id')

            if usuario_id is None:
                messagebox.showwarning("Aviso", "Não foi possível determinar o id do usuário.", parent=dlg)
                return

            # Update para associar sala
            sql_update = f"UPDATE Usuario SET sala_id = {codigo_int} WHERE id = {usuario_id};"
            requestBD(sql_update)
            messagebox.showinfo("Entrou", f"{nome} entrou na sala {codigo_int}.", parent=dlg)
            # se a sala atual for a mesma, atualiza a lista
            if current_sala_id == codigo_int:
                atualizar_lista_usuarios()
            dlg.destroy()
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível entrar na sala.\n\n{e}", parent=dlg)

    ttk.Button(dlg, text="Confirmar", command=_confirmar, bootstyle=SUCCESS).pack(pady=10)
    ttk.Button(dlg, text="Cancelar", command=dlg.destroy, bootstyle=SECONDARY).pack()

# -------------------------
# Código da sala
# -------------------------
code_frame = ttk.Labelframe(app, text="CÓDIGO DA SALA", padding=10)
code_frame.pack(fill=X, padx=10, pady=5)

code_var = tk.StringVar(value="(nenhuma)")
code_label = ttk.Label(code_frame, textvariable=code_var, font=("Segoe UI", 14))
code_label.pack(side=LEFT, padx=5)

copy_btn = ttk.Button(code_frame, text="Copiar", bootstyle=INFO, command=lambda: app.clipboard_append(code_var.get()))
copy_btn.pack(side=LEFT, padx=5)

# iniciar auto-refresh sempre ativo
start_auto_refresh()

def _on_close():
    stop_auto_refresh()
    try:
        app.destroy()
    except Exception:
        pass

app.protocol("WM_DELETE_WINDOW", _on_close)
app.mainloop()