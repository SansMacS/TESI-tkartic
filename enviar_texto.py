import tkinter as tk
from tkinter import ttk
import ttkbootstrap as tb
from ttkbootstrap.constants import *
import requesicao
from datetime import datetime
import variaveis_globais
import control
import os
import canva_modificado
from tkinter import messagebox

class WritePhraseScreen:
    def __init__(self, root, duration=30, parent_to_restore=None):
        self.root = root
        self.duration = duration
        self.remaining = duration
        self.running = False
        # parent_to_restore: janela (Toplevel) que deve ser restaurada ao fechar esta tela
        self.parent_to_restore = parent_to_restore

        self.root.title("Tkartic - Escreva uma frase")
        self.root.geometry("1200x780")
        # Try to initialize ttkbootstrap Style; if that creates issues when using a plain Toplevel,
        # fallback to tkinter.ttk.Style. Also log root type for diagnostic.
        try:
            print(f"[DEBUG] WritePhraseScreen.__init__ root type: {type(self.root)}")
            self.style = tb.Style(theme="superhero")
        except Exception as e:
            print('[DEBUG] tb.Style failed, falling back to ttk.Style():', e)
            try:
                self.style = ttk.Style()
            except Exception as e2:
                print('[DEBUG] ttk.Style fallback also failed:', e2)
                self.style = None

        self._build_ui()
        self.start_countdown()
        # gerencia fechamento da janela para restaurar parent, se houver
        try:
            self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        except Exception:
            pass

    def _build_ui(self):
        pad = 18

        # Top area (logo)
        top = ttk.Frame(self.root, padding=(pad, pad // 2))
        top.pack(fill=X)
        ttk.Label(top, text="Tkartic", font=("Segoe UI", 28, "bold"), foreground="#17A2B8").pack()

        # Container principal dividido em centro e rodapé de controles
        center = ttk.Frame(self.root, padding=(pad, 12))
        center.pack(fill=BOTH, expand=YES)

        # Instrução grande central
        ttk.Label(center, text="ESCREVA UMA FRASE", font=("Segoe UI", 20, "bold"), foreground="#17A2B8").pack(pady=(4, 16))

        # Expande espaço central para empurrar os controles para baixo
        content_spacer = ttk.Frame(center)
        content_spacer.pack(fill=BOTH, expand=YES)

        # Agrupar entrada e botões em um footer interno dentro da área central
        input_container = ttk.Frame(center, padding=(0, 12))
        input_container.pack(fill=X)

        self.entry_var = tk.StringVar(value="Toureiro gordo na novela")
        self.entry = ttk.Entry(input_container, textvariable=self.entry_var, font=("Segoe UI", 16))
        self.entry.pack(side=LEFT, fill=X, expand=YES, ipady=12, padx=(0, 12))

        self.ready_btn = ttk.Button(input_container, text="PRONTO!", bootstyle=(PRIMARY, "outline"), command=self.on_ready)
        self.ready_btn.pack(side=LEFT)

        # Area de tempo e explicação logo abaixo da entrada (na parte inferior da janela)
        timer_card = ttk.Frame(self.root, padding=12)
        timer_card.pack(side=BOTTOM, fill=X)

        # Tempo grande à esquerda do cartão (cores mais claras)
        self.time_label = ttk.Label(timer_card, text=f"Tempo restante: {self.remaining}s",
                                    font=("Segoe UI", 18, "bold"), foreground="#e6b800")
        self.time_label.pack(anchor=W, padx=(6, 12))

        # Barra de progresso larga e discreta
        self.progress = ttk.Progressbar(timer_card, bootstyle="info", mode="determinate")
        self.progress.pack(fill=X, pady=(10, 4), padx=6)
        self.progress["maximum"] = self.duration
        self.progress["value"] = self.duration

        # Texto explicativo abaixo da barra (mais visível, cor clara)
        self.hint_label = ttk.Label(timer_card, text="A frase que você escrever será desenhada pelos outros jogadores",
                                    font=("Segoe UI", 13, "bold"), foreground="#444444")
        self.hint_label.pack(anchor=W, padx=6, pady=(6, 0))

        # Rodapé com informações menores
        footer = ttk.Frame(self.root, padding=(pad, 10))
        footer.pack(fill=X, side=BOTTOM)
        ttk.Label(footer, text="Dica: seja claro e criativo para que o desenho seja mais fácil de interpretar",
                  font=("Segoe UI", 10)).pack(anchor=W)

    def start_countdown(self):
        if self.running:
            return
        self.running = True
        print('[DEBUG] WritePhraseScreen.start_countdown called, scheduling _tick')
        try:
            self._tick()
        except Exception as e:
            print('[DEBUG] start_countdown _tick error:', e)

    def _tick(self):
        # Atualiza texto e barra de progresso
        print(f"[DEBUG] WritePhraseScreen._tick remaining={self.remaining}")
        self.time_label.config(text=f"Tempo restante: {self.remaining}s")
        self.progress["value"] = max(0, self.remaining)
        # Muda cor do texto e estilo da barra nos últimos 10 segundos (tons claros)
        if self.remaining <= 10 and self.remaining > 0:
            self.time_label.config(foreground="#ff6b6b")
            self.progress.configure(bootstyle="danger")
        else:
            self.time_label.config(foreground="#e6b800")
            self.progress.configure(bootstyle="info")

        if self.remaining <= 0:
            self._time_up()
            return
        self.remaining -= 1
        self.root.after(1000, self._tick)

    def _time_up(self):
        self.running = False
        print('[DEBUG] WritePhraseScreen._time_up entered')
        self.entry.state(["disabled"])
        self.ready_btn.state(["disabled"])
        self.time_label.config(text="Tempo esgotado", foreground="#bdbdbd")
        self.progress["value"] = 0
        self.progress.configure(bootstyle="secondary")
        # Envia a frase automaticamente quando o tempo acaba
        try:
            phrase = self.entry_var.get().strip()
            if phrase:
                self._send_phrase_to_server(phrase)
        except Exception:
            pass
        # após timeout, faz a transição automática para o canvas
        try:
            print('[DEBUG] enviar_texto: tempo esgotado, abrindo canvas')
            self._fechar_e_abrir_canvas()
        except Exception as e:
            print('[DEBUG] erro ao abrir canvas no time_up:', e)
            pass

    def on_ready(self):
        phrase = self.entry_var.get().strip()
        self.entry.state(["disabled"])
        self.ready_btn.state(["disabled"])
        self.running = False
        self.time_label.config(text="Pronto enviado", foreground="#72f5b6")
        self.progress["value"] = 0
        print("Frase enviada:", phrase)
        # Envia imediatamente ao servidor
        try:
            if phrase:
                # usa controller para inserir frase quando não pertence a sala
                if getattr(variaveis_globais, 'sala_id', None):
                    ctrl = control.ControllerSala()
                    ctrl.inserir_chat(variaveis_globais.sala_id, (variaveis_globais.jogador[1] if variaveis_globais.jogador else 'Anon'), phrase)
                else:
                    ctrlf = control.ControllerFrase()
                    ctrlf.inserir_frase(phrase, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                messagebox.showinfo('Sucesso', 'Frase enviada.')
        except Exception as e:
            messagebox.showwarning('Aviso', f'Erro ao enviar frase: {e}')
        # Abre o canvas após envio manual também (não destrói a janela antes)
        try:
            print('[DEBUG] enviar_texto: PRONTO pressionado, abrindo canvas')
            self._fechar_e_abrir_canvas()
        except Exception as e:
            print('[DEBUG] erro ao abrir canvas on_ready:', e)
            pass

    def _fechar_e_abrir_canvas(self):
        # Abre o canvas embutido em uma nova Toplevel, passando o texto
        try:
            import canva_modificado
            print('[DEBUG] enviar_texto: criando Toplevel para canvas')
            canva_win = tk.Toplevel()

            def on_canvas_finish(saved_path):
                # após terminar desenho, abrir exibir_album com texto+imagem
                print('[DEBUG] enviar_texto: on_canvas_finish called with', saved_path)
                try:
                    import exibir_album
                    alb_win = tk.Toplevel()
                    # construir uma sequência simples com o texto e a imagem
                    seq = []
                    seq.append(('text', self.entry_var.get().strip(), None))
                    if saved_path:
                        seq.append(('drawing', saved_path, None))
                    exibir_album.GarticAlbumApp(alb_win, sequence_override=seq)
                except Exception:
                    try:
                        messagebox.showinfo('Ação necessária', 'Abra o álbum manualmente para ver resultados.')
                    except Exception:
                        pass

            print('[DEBUG] enviar_texto: instanciando canva_modificado.Paint')
            app_canva = canva_modificado.Paint(master=canva_win, initial_text=self.entry_var.get().strip(), countdown_seconds=120, on_finish=on_canvas_finish)
            print('[DEBUG] enviar_texto: Paint instanciado, callback wired')

            # depois que o canvas for criado com sucesso, podemos fechar a tela de escrever frase
            try:
                if self.parent_to_restore:
                    try:
                        self.parent_to_restore.deiconify()
                    except Exception:
                        pass
            except Exception:
                pass

            try:
                self.root.destroy()
            except Exception:
                pass

        except Exception as e:
            print('[DEBUG] falha ao abrir canvas:', e)
            try:
                messagebox.showinfo('Ação necessária', "Não foi possível abrir a tela de desenho automaticamente. Abra 'canva_modificado.py' manualmente")
            except Exception:
                pass

    def _escape_sql(self, text: str) -> str:
        # Escapa aspas simples para evitar quebra de query (não é proteção completa contra injeção)
        return text.replace("'", "''")

    def _send_phrase_to_server(self, phrase: str):
        # Monta SQL e envia via requesicao.requestBD
        safe = self._escape_sql(phrase)
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # se estivermos em uma sala, gravamos na tabela Chat, caso contrário na tabela Frase
        sala = getattr(variaveis_globais, 'sala_id', None)
        usuario = None
        try:
            usuario = variaveis_globais.jogador[1] if variaveis_globais.jogador else 'Anon'
        except Exception:
            usuario = 'Anon'

        try:
            if sala:
                u = str(usuario).replace("'", "''")
                sql = f"INSERT INTO Chat (sala_id, usuario, mensagem, ts) VALUES ({sala}, '{u}', '{safe}', '{ts}');"
            else:
                sql = f"INSERT INTO Frase (texto, criado_em) VALUES ('{safe}', '{ts}');"
            resp = requesicao.requestBD(sql)
            print('Resposta servidor (inserir frase):', resp)
            return resp
        except Exception as e:
            print('Erro na requisição ao servidor:', e)
            # fallback: salva localmente se o servidor não estiver acessível
            try:
                pasta = 'local_phrases'
                os.makedirs(pasta, exist_ok=True)
                caminho = os.path.join(pasta, 'phrases_local.txt')
                with open(caminho, 'a', encoding='utf-8') as f:
                    f.write(f"[{ts}] {usuario}: {phrase}\n")
                print('Gravado localmente em', caminho)
            except Exception:
                pass

    def _on_close(self):
        # restaura parent_to_restore se foi fornecido
        try:
            if self.parent_to_restore:
                try:
                    self.parent_to_restore.deiconify()
                except Exception:
                    pass
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass

if __name__ == "__main__":
    root = tb.Window(themename="superhero")
    app = WritePhraseScreen(root, duration=30)
    root.mainloop()