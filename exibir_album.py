import tkinter as tk
from tkinter import ttk
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from PIL import Image, ImageTk, ImageDraw, ImageFont
from control import ControllerAlbum

class SequenceItem:
    """Representa um item na sequência: pode ser texto ou desenho (imagem)."""
    def __init__(self, kind, content, author=None):
        self.kind = kind  # 'text' or 'drawing'
        self.content = content
        self.author = author

class GarticAlbumApp:
    def __init__(self, master, sequence_override=None):
        self.master = master
        self.master.title("Gartic Album - Visualizador")
        try:
            self.master.geometry("1200x780")
        except Exception:
            pass
        self.style = tb.Style(theme="darkly")  # tema agradável escuro
        self.players = ["Lev", "Amelia", "Ken", "Douglass"]

        self._build_ui()
        # If a sequence_override is provided, use it. Expected format: list of tuples (kind, content, author)
        if sequence_override:
            self.sequence = []
            for k, c, a in sequence_override:
                if k == 'drawing':
                    try:
                        img = Image.open(c)
                        self.sequence.append(SequenceItem('drawing', ImageTk.PhotoImage(img), author=a))
                    except Exception:
                        self.sequence.append(SequenceItem('text', str(c), author=a))
                else:
                    self.sequence.append(SequenceItem('text', c, author=a))
        else:
            if not self._load_from_server():
                self._load_sample_sequence()
        self.current_index = 0
        self._show_sequence_items()
        self._highlight_current()

    def _build_ui(self):
        # Main layout: left (players) and right (album)
        self.main_frame = ttk.Frame(self.master)
        self.main_frame.pack(fill=BOTH, expand=YES, padx=12, pady=12)

        # Left panel: players Listbox
        left_frame = ttk.Frame(self.main_frame, width=200)
        left_frame.pack(side=LEFT, fill=Y, padx=(0,12))
        ttk.Label(left_frame, text="Players", font=("Segoe UI", 12, "bold")).pack(anchor=W)
        self.players_var = tk.StringVar(value=self.players)
        self.players_listbox = tk.Listbox(
            left_frame, listvariable=self.players_var, height=20, activestyle='none',
            selectmode=SINGLE, exportselection=False
        )
        self.players_listbox.pack(fill=Y, expand=YES, pady=(6,0))
        # Select the first player by default
        self.players_listbox.selection_set(0)

        # Right panel: album with scrollable sequence
        right_frame = ttk.Frame(self.main_frame)
        right_frame.pack(side=LEFT, fill=BOTH, expand=YES)

        header = ttk.Label(right_frame, text="Douglass's Album", font=("Segoe UI", 14, "bold"))
        header.pack(anchor=W)

        # Scrollable canvas area
        self.canvas_container = ttk.Frame(right_frame)
        self.canvas_container.pack(fill=BOTH, expand=YES, pady=(6,6))

        self.canvas = tk.Canvas(self.canvas_container, background=self.style.colors.bg, highlightthickness=0)
        self.vscroll = ttk.Scrollbar(self.canvas_container, orient=VERTICAL, command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vscroll.set)

        self.vscroll.pack(side=RIGHT, fill=Y)
        self.canvas.pack(side=LEFT, fill=BOTH, expand=YES)

        # Internal frame that will hold sequence item widgets
        self.items_frame = ttk.Frame(self.canvas)
        self.items_window = self.canvas.create_window((0, 0), window=self.items_frame, anchor="nw")

        # Bind configure events for proper scrolling
        self.items_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        # Bottom control area: voting and next button
        controls_frame = ttk.Frame(right_frame)
        controls_frame.pack(fill=X, pady=(6,0))

        vote_frame = ttk.Frame(controls_frame)
        vote_frame.pack(side=LEFT, padx=(0,12))

        ttk.Label(vote_frame, text="Voto", font=("Segoe UI", 10, "bold")).pack(anchor=W)
        self.vote_var = tk.IntVar(value=0)
        # Use Radiobuttons for single-choice voting 1..5
        for i in range(1,6):
            rb = ttk.Radiobutton(vote_frame, text=str(i), variable=self.vote_var, value=i)
            rb.pack(side=LEFT, padx=4)

        # Próximo button
        self.next_btn = ttk.Button(controls_frame, text="Próximo", bootstyle=(PRIMARY, SECONDARY), command=self._on_next)
        self.next_btn.pack(side=LEFT)

    def _on_frame_configure(self, event):
        # Update scroll region to match inner frame size
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        # Make the inner frame the same width as the canvas
        canvas_width = event.width
        self.canvas.itemconfigure(self.items_window, width=canvas_width)

    def _load_sample_sequence(self):
        # Amostra de itens baseados na imagem referenciada
        self.sequence = []
        self.sequence.append(SequenceItem("text", "Ken's prompt: Accidentally buying a movie theater", author="Ken"))
        # Create a simple drawing placeholder image that resembles a stick figure + screen with "Oops"
        img1 = self._create_drawing_placeholder("stick figure with 'Oops' and movie screen")
        self.sequence.append(SequenceItem("drawing", img1, author="Ken"))
        self.sequence.append(SequenceItem("text", "Amelia's guess: A person accidentally buys something on", author="Amelia"))

    def _load_from_server(self):
        try:
            ctrl = ControllerAlbum()
            resp = ctrl.listar_sequencia(1)
            if not resp:
                return False
            rows = resp
            seq = []
            for r in rows:
                if isinstance(r, dict):
                    kind = r.get('tipo')
                    content = r.get('conteudo')
                    author = r.get('autor')
                elif isinstance(r, (list, tuple)):
                    kind, content, author = (r[0], r[1], r[2])
                else:
                    continue
                if kind == 'drawing':
                    # assume content is path
                    try:
                        img = Image.open(content)
                        seq.append(SequenceItem('drawing', ImageTk.PhotoImage(img), author=author))
                    except Exception:
                        pass
                else:
                    seq.append(SequenceItem('text', content, author=author))
            if seq:
                self.sequence = seq
                return True
            return False
        except Exception:
            return False

    def _create_drawing_placeholder(self, caption, size=(560,220)):
        # Create a PIL image as a simple drawing placeholder (will be shown on Canvas)
        img = Image.new("RGBA", size, (255,255,255,255))
        draw = ImageDraw.Draw(img)
        w,h = size
        # background rectangles to simulate screen
        draw.rectangle([20,20,w-20,h-20], fill=(245,245,245), outline=(180,180,180))
        # simple "screen" with two stick figures inside
        draw.rectangle([320,40,520,140], fill=(20,20,40))
        # stick figures on the screen
        draw.ellipse([340,50,360,70], outline="white", width=2)
        draw.line([350,70,350,100], fill="white", width=2)
        draw.line([350,80,340,90], fill="white", width=2)
        draw.line([350,80,360,90], fill="white", width=2)
        # outside stick figure with speech bubble
        draw.ellipse([60,60,90,90], outline="black", width=2)
        draw.line([75,90,75,140], fill="black", width=2)
        draw.line([75,110,60,120], fill="black", width=2)
        draw.line([75,110,90,120], fill="black", width=2)
        # speech bubble
        draw.rectangle([100,40,170,80], fill="white", outline="black")
        draw.text((110,48), "Oops", fill="black")
        # caption text
        try:
            fnt = ImageFont.truetype("arial.ttf", 12)
        except Exception:
            fnt = ImageFont.load_default()
        draw.text((24,160), caption, fill=(30,30,30), font=fnt)
        return ImageTk.PhotoImage(img)

    def _show_sequence_items(self):
        # Clear existing children in items_frame
        for child in self.items_frame.winfo_children():
            child.destroy()

        self.item_widgets = []
        for idx, item in enumerate(self.sequence):
            card = ttk.Frame(self.items_frame, padding=8, style="secondary.TFrame")
            card.pack(fill=X, pady=6, padx=6)

            header_text = f"{item.author or 'Unknown'}"
            ttk.Label(card, text=header_text, font=("Segoe UI", 10, "bold")).pack(anchor=W)

            if item.kind == "text":
                lbl = ttk.Label(card, text=item.content, wraplength=700, justify=LEFT)
                lbl.pack(anchor=W, pady=(6,0))
                self.item_widgets.append(card)
            elif item.kind == "drawing":
                # place the image inside a label
                img_lbl = ttk.Label(card, image=item.content)
                img_lbl.image = item.content  # keep reference
                img_lbl.pack(anchor=W, pady=(6,0))
                self.item_widgets.append(card)

    def _highlight_current(self):
        # Visually indicate the current item in the list (simple border change)
        for i, w in enumerate(self.item_widgets):
            style = "secondary.TFrame" if i != self.current_index else "success.TFrame"
            w.configure(style=style)
            # Scroll to the current widget:
            if i == self.current_index:
                self.master.after(10, lambda w=w: self._scroll_to_widget(w))

    def _scroll_to_widget(self, widget):
        # Get widget bbox relative to canvas and scroll so widget top is visible
        self.canvas.update_idletasks()
        try:
            widget_y = widget.winfo_rooty() - self.canvas.winfo_rooty() + self.canvas.canvasy(0)
            self.canvas.yview_moveto(max(0, widget_y / max(1, self.items_frame.winfo_height())))
        except Exception:
            pass

    def _on_next(self):
        # Save current vote (here we just print it; in a real app we'd store it linked to the current item)
        print(f"Voto para item {self.current_index}: {self.vote_var.get()}")
        # Advance index
        if self.current_index < len(self.sequence) - 1:
            self.current_index += 1
        else:
            # Se já no fim, volta ao começo
            self.current_index = 0
        self._highlight_current()

if __name__ == "__main__":
    root = tb.Window(themename="superhero")
    app = GarticAlbumApp(root)
    root.mainloop()