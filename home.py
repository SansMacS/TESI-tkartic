import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import tkinter as tk
import control 
import requesicao
import variaveis_globais
from sala_de_espera import open_waiting_room

class TelaHome:
    def __init__(self, master):
        self.janela = master
        self.janela.title("TKARTIC™")
        self.janela.geometry("1200x780")
        self.janela.resizable(False, False)
        self.janela.configure(bg="#1E3A8A")

        # Container principal
        self.container = tk.Frame(self.janela, bg="#1E3A8A")
        self.container.pack(fill="both", expand=True)

        # Título
        titulo = tk.Label(
            self.container, text="TKARTIC™",
            font=("Arial", 48, "bold"),
            fg="white", bg="#1E3A8A"
        )
        titulo.pack(pady=(30, 10))

        # Botões centrais
        botoes_frame = tk.Frame(self.container, bg="#1E3A8A")
        botoes_frame.pack(expand=True)

        btn_entrar = ttk.Button(
            botoes_frame, text="Entrar na Sala",
            bootstyle=PRIMARY, width=25, padding=20,
            command=self.abrir_inserir_codigo
        )
        btn_entrar.pack(pady=25)

        btn_criar = ttk.Button(
            botoes_frame, text="Criar Sala",
            bootstyle=INFO, width=25, padding=20, command=self.criar_sala)
        btn_criar.pack(pady=25)

        # Botão SAIR
        btn_sair = ttk.Button(
            self.container, text="SAIR",
            bootstyle=DANGER, width=10,
            command=self.janela.destroy
        )
        btn_sair.place(relx=0.95, rely=0.95, anchor="se")

    def criar_sala(self):
        """Cria uma nova sala no banco de dados"""
        controlador_sala = control.ControllerSala()
        resultado = controlador_sala.inserir_sala()
        # DEBUG: mostrar retorno bruto da criação de sala para diagnóstico
        try:
            print(f"[DEBUG] inserir_sala retorno: {resultado}")
        except Exception:
            pass
        # resultado pode ser resposta do servidor; tentamos extrair id
        try:
            sala_id = None
            if isinstance(resultado, dict):
                for key in ('lastrowid', 'id', 'inserted_id'):
                    if key in resultado:
                        sala_id = resultado[key]
                        break
            elif isinstance(resultado, (int, str)):
                try:
                    sala_id = int(resultado)
                except Exception:
                    sala_id = None

            # fallback: consultar ultima sala criada (trata wrapper da requestBD)
            if sala_id is None:
                try:
                    q = "SELECT id FROM Sala ORDER BY id DESC LIMIT 1;"
                    r2 = requesicao.requestBD(q)
                except Exception:
                    r2 = None

                rows = None
                # requestBD agora retorna um wrapper dict {'ok','payload',...}
                if isinstance(r2, dict) and 'payload' in r2:
                    rows = r2.get('payload')
                else:
                    rows = r2

                if isinstance(rows, list) and len(rows) > 0:
                    first = rows[0]
                    if isinstance(first, (list, tuple)):
                        sala_id = first[0]
                    elif isinstance(first, dict):
                        sala_id = first.get('id')

            if sala_id is None:
                tk.messagebox.showwarning("Aviso", "Sala criada, mas não foi possível obter o id.")
                return

            variaveis_globais.sala_id = int(sala_id)

            # associa o usuário atual à sala (se tivermos info do jogador)
            try:
                if variaveis_globais.jogador:
                    usuario_id = variaveis_globais.jogador[0]
                    ctrl_user = control.ControllerUsuario()
                    ctrl_user.associar_usuario_sala(usuario_id, variaveis_globais.sala_id)
            except Exception:
                pass

            tk.messagebox.showinfo("Sucesso", "Sala criada com sucesso!")
            # abre sala de espera como host -> esconde a home e restaura quando a sala for fechada
            try:
                self.janela.withdraw()
                top = open_waiting_room(self.janela, variaveis_globais.sala_id, is_host=True, username=(variaveis_globais.jogador[1] if variaveis_globais.jogador else None))

                # quando a sala for fechada, destrói o Toplevel e mostra a home novamente
                def ao_fechar_sala():
                    try:
                        top.destroy()
                    except Exception:
                        pass
                    try:
                        self.janela.deiconify()
                    except Exception:
                        pass

                try:
                    top.protocol("WM_DELETE_WINDOW", ao_fechar_sala)
                except Exception:
                    pass
            except Exception as e:
                tk.messagebox.showerror("Erro", f"Falha ao abrir sala de espera: {e}")
        except Exception as e:
            tk.messagebox.showerror("Erro", f"Falha ao criar a sala: {e}")

        


    def abrir_inserir_codigo(self):
        """Abre a tela Inserir Código"""
        top = tk.Toplevel(self.janela)
        top.title("Inserir Código")
        top.geometry("500x300")
        top.configure(bg="#1E3A8A")
        top.resizable(False, False)

        # Botão X (fechar)
        btn_fechar = tk.Button(
            top, text="X", font=("Arial", 12, "bold"),
            fg="white", bg="#1E3A8A", bd=0,
            command=top.destroy
        )
        btn_fechar.place(relx=0.95, rely=0.05, anchor="ne")

        # Título
        lbl_titulo = tk.Label(
            top, text="INSERIR CÓDIGO",
            font=("Arial", 20, "bold"),
            fg="white", bg="#1E3A8A"
        )
        lbl_titulo.pack(pady=(30, 20))

        # Campo de entrada + ícone
        entry_frame = tk.Frame(top, bg="#1E3A8A")
        entry_frame.pack(pady=20)

        entry_codigo = ttk.Entry(entry_frame, font=("Arial", 16), width=20)
        entry_codigo.pack(side="left", padx=(0, 10))

        icon = tk.Label(
            entry_frame, text="🔢", font=("Arial", 18),
            bg="#1E3A8A", fg="white"
        )
        icon.pack(side="left")

        # Botões Cancelar e Confirmar
        botoes_frame = tk.Frame(top, bg="#1E3A8A")
        botoes_frame.pack(side="bottom", pady=30)

        btn_cancelar = ttk.Button(
            botoes_frame, text="CANCELAR",
            bootstyle=SECONDARY, width=12,
            command=top.destroy
        )
        btn_cancelar.pack(side="left", padx=20)

        def confirmar_codigo():
            codigo = entry_codigo.get().strip()
            if not codigo:
                tk.messagebox.showwarning("Aviso", "Informe o código da sala.", parent=top)
                return
            try:
                sala_id = int(codigo)
                variaveis_globais.sala_id = sala_id
                open_waiting_room(self.janela, sala_id, is_host=False, username=(variaveis_globais.jogador[1] if variaveis_globais.jogador else None))
                top.destroy()
            except Exception as e:
                tk.messagebox.showerror("Erro", f"Não foi possível entrar na sala: {e}", parent=top)

        btn_confirmar = ttk.Button(botoes_frame, text="CONFIRMAR", bootstyle=SUCCESS, width=12, command=confirmar_codigo)
        btn_confirmar.pack(side="left", padx=20)


if __name__ == "__main__":
    app = ttk.Window(themename="flatly")
    TelaHome(app)
    app.mainloop()