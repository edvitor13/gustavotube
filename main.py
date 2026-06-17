import os
import sys
import shutil
import urllib.request
import zipfile
import tempfile
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import yt_dlp
import threading
import re

# === Gerenciamento do FFmpeg ===

FFMPEG_DIR = os.path.join(
    os.environ.get('APPDATA', os.path.expanduser('~')),
    'GustavoTube', 'bin'
)
ffmpeg_location = None  # None = usar ffmpeg do PATH do sistema


def _find_local_ffmpeg():
    """Retorna FFMPEG_DIR se o binário existir lá, caso contrário None."""
    exe = 'ffmpeg.exe' if os.name == 'nt' else 'ffmpeg'
    return FFMPEG_DIR if os.path.isfile(os.path.join(FFMPEG_DIR, exe)) else None


def ensure_ffmpeg(on_ready, on_error=None):
    """
    Garante que o ffmpeg está disponível.
    Chama on_ready() quando pronto; faz download automático se necessário.
    """
    global ffmpeg_location

    if shutil.which('ffmpeg'):       # Encontrado no PATH do sistema
        ffmpeg_location = None
        on_ready()
        return

    loc = _find_local_ffmpeg()       # Encontrado no cache local
    if loc:
        ffmpeg_location = loc
        on_ready()
        return

    _download_ffmpeg(on_ready, on_error)  # Precisa baixar


def _download_ffmpeg(on_ready, on_error=None):
    """Baixa o FFmpeg para FFMPEG_DIR exibindo uma janela de progresso."""
    global ffmpeg_location

    win = tk.Toplevel(root)
    win.title("Baixando dependências")
    win.resizable(False, False)
    win.grab_set()

    w, h = 440, 135
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    win.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

    ttk.Label(
        win,
        text="Baixando FFmpeg (necessário para conversão)...",
        font=('', 10)
    ).pack(padx=20, pady=(18, 6))

    progress_var = tk.DoubleVar()
    bar = ttk.Progressbar(win, variable=progress_var, maximum=100, length=400)
    bar.pack(padx=20, pady=4)

    status_lbl = ttk.Label(win, text="Conectando...")
    status_lbl.pack(pady=(4, 0))

    def set_ui(text, pct=None):
        status_lbl.config(text=text)
        if pct is not None:
            progress_var.set(pct)

    def worker():
        global ffmpeg_location
        try:
            os.makedirs(FFMPEG_DIR, exist_ok=True)

            if os.name == 'nt':
                url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
                targets = {'ffmpeg.exe', 'ffprobe.exe'}
                archive_type = 'zip'
            else:
                url = "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
                targets = {'ffmpeg', 'ffprobe'}
                archive_type = 'tar'

            tmp_path = os.path.join(tempfile.gettempdir(), 'ffmpeg_dl_tmp')

            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=120) as resp:
                total = int(resp.headers.get('Content-Length', 0))
                downloaded = 0
                with open(tmp_path, 'wb') as f:
                    while True:
                        data = resp.read(65536)
                        if not data:
                            break
                        f.write(data)
                        downloaded += len(data)
                        if total:
                            pct = downloaded * 100 / total
                            d_mb = downloaded / 1048576
                            t_mb = total / 1048576
                            win.after(0, lambda p=pct, d=d_mb, t=t_mb:
                                      set_ui(f"Baixando... {int(p)}%  ({d:.1f} MB / {t:.1f} MB)", p))

            win.after(0, lambda: set_ui("Extraindo...", 100))

            if archive_type == 'zip':
                with zipfile.ZipFile(tmp_path, 'r') as zf:
                    for name in zf.namelist():
                        if os.path.basename(name) in targets:
                            dest = os.path.join(FFMPEG_DIR, os.path.basename(name))
                            with zf.open(name) as src, open(dest, 'wb') as dst:
                                dst.write(src.read())
            else:
                import tarfile
                with tarfile.open(tmp_path, 'r:xz') as tf:
                    for member in tf.getmembers():
                        if os.path.basename(member.name) in targets:
                            fname = os.path.basename(member.name)
                            source = tf.extractfile(member)
                            if source:
                                dest = os.path.join(FFMPEG_DIR, fname)
                                with open(dest, 'wb') as dst:
                                    dst.write(source.read())
                                os.chmod(dest, 0o755)

            os.remove(tmp_path)
            ffmpeg_location = FFMPEG_DIR

            def finish():
                win.destroy()
                on_ready()
            win.after(0, finish)

        except Exception as exc:
            def handle_err():
                win.destroy()
                if on_error:
                    on_error(str(exc))
                else:
                    messagebox.showerror(
                        "Erro",
                        f"Falha ao baixar FFmpeg:\n{exc}\n\n"
                        "Instale o FFmpeg manualmente e adicione ao PATH."
                    )
            win.after(0, handle_err)

    threading.Thread(target=worker, daemon=True).start()


def update_selector(*args):
    format_choice = format_var.get()
    if format_choice == "MP3":
        resolution_label.config(text="Qualidade do áudio:")
        resolution_dropdown['values'] = ("320", "256", "192", "128", "64")
        resolution_var.set("320") 
    else:
        resolution_label.config(text="Resolução do video:")
        resolution_dropdown['values'] = [
            "2160 (4K)", 
            "1440 (2K)", 
            "1080 (FHD)", 
            "720 (HD)", 
            "480 (SD)", 
            "360 (SD)", 
            "240 (SD)", 
            "144 (SD)"
        ]
        resolution_var.set("1080 (FHD)") 

def download_video():
    url = url_entry.get()
    format_choice = format_var.get()
    resolution_choice = resolution_var.get()

    # Extrai apenas o valor numérico da resolução
    resolution_choice = resolution_choice.split(" ")[0] 

    if not url:
        messagebox.showwarning("Input Error", "Por favor, insira uma URL do YouTube.")
        return

    # Extrai o nome do vídeo sem baixar
    with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
        info = ydl.extract_info(url, download=False)
        default_filename = ydl.prepare_filename(info).rsplit(".", 1)[0]  # Obtém o nome original do vídeo

    # Abre o diálogo para escolher o local e o nome do arquivo
    save_path = filedialog.asksaveasfilename(
        initialdir=".", 
        title="Salvar arquivo como", 
        initialfile=default_filename, 
        defaultextension=f".{format_choice.lower()}",
        filetypes=[(f"Arquivo {format_choice}", f"*.{format_choice.lower()}")]
    )
    
    if not save_path:
        return  # O usuário cancelou a seleção

    ydl_opts = {}

    def download_thread():
        try:
            if format_choice == "MP4":
                ydl_opts = {
                    'format': f'bestvideo[height<={resolution_choice}][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<={resolution_choice}]+bestaudio/best',
                    'outtmpl': save_path,  # Salva no caminho escolhido
                    'merge_output_format': 'mp4',
                    'postprocessors': [{
                        'key': 'FFmpegVideoConvertor',
                        'preferedformat': 'mp4',
                    }],
                    'postprocessor_args': [
                        '-c:v', 'libx264',
                        '-preset', 'slow',
                        '-crf', '18',
                        '-c:a', 'aac',
                        '-b:a', '320k',
                    ],
                    'progress_hooks': [my_hook],
                }
            elif format_choice == "MP3":
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': resolution_choice,
                    }],
                    'outtmpl': save_path, 
                    'progress_hooks': [my_hook],
                }

            if ffmpeg_location:
                ydl_opts['ffmpeg_location'] = ffmpeg_location

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            messagebox.showinfo("Sucesso", "Download concluído!")
            progress_window.destroy()
            progress_window.grab_release()

            # Abre o diretório com o arquivo selecionado
            open_file_directory(save_path)

        except Exception as e:
            messagebox.showerror("Erro", f"Ocorreu um erro ao baixar o vídeo: {str(e)}")
            progress_window.destroy()
            progress_window.grab_release()

    # Cria uma nova janela para a barra de progresso
    progress_window = tk.Toplevel(root)
    progress_window.title("Baixando...")
    progress_window.grab_set()  # Trava a tela principal

    # Centraliza a janela de progresso e define a largura
    progress_window.update_idletasks()
    screen_width = progress_window.winfo_screenwidth()
    screen_height = progress_window.winfo_screenheight()
    window_width = 300  # Define a largura desejada
    window_height = 100
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    progress_window.geometry(f"{window_width}x{window_height}+{x}+{y}")

    progress_var = tk.DoubleVar()
    progress_bar = ttk.Progressbar(progress_window, variable=progress_var, maximum=100)
    progress_bar.pack(padx=20, pady=20)

    progress_label = ttk.Label(progress_window, text="0%")
    progress_label.pack()

    # Função para atualizar a barra de progresso
    def my_hook(d):
        if d['status'] == 'downloading':
            p = d['_percent_str']
            # Remove caracteres de escape ANSI antes da conversão
            p = re.sub(r'\x1b\[[0-9;]*m', '', p) 
            p = float(p.replace('%', ''))
            progress_var.set(p)
            progress_label.config(text=f"{int(p)}%") 
            if int(p) >= 100:
                progress_window.title("Convertendo...")
                progress_label.config(text=f"Convertendo para MP4...") 
            progress_window.update_idletasks()

    # Inicia o download em uma thread separada
    threading.Thread(target=download_thread).start()

def open_file_directory(file_path):
    folder_path = os.path.dirname(file_path)
    file_name = os.path.basename(file_path)
    
    if os.name == 'nt':  # Windows
        os.startfile(folder_path)  # Abre o diretório
    elif os.name == 'posix':  # Linux, MacOS
        os.system(f'xdg-open "{folder_path}"')
    else:
        messagebox.showwarning("Erro", "Sistema operacional não suportado para abrir diretório.")

# Configuração da janela principal
root = tk.Tk()
root.title("GustavoTube 2.0")
root.withdraw()  # Oculta até o FFmpeg estar pronto

# Widgets
url_label = ttk.Label(root, text="URL do vídeo:")
url_label.grid(column=0, row=0, padx=10, pady=10)
url_entry = ttk.Entry(root, width=50)
url_entry.grid(column=1, row=0, padx=10, pady=10)

format_label = ttk.Label(root, text="Formato:")
format_label.grid(column=0, row=1, padx=10, pady=10)
format_var = tk.StringVar(value="MP4")
format_mp4 = ttk.Radiobutton(root, text="MP4", variable=format_var, value="MP4")
format_mp4.grid(column=1, row=1, sticky="W", padx=10)
format_mp3 = ttk.Radiobutton(root, text="MP3", variable=format_var, value="MP3")
format_mp3.grid(column=1, row=1, padx=80)

resolution_label = ttk.Label(root, text="Resolução do video:")
resolution_label.grid(column=0, row=2, padx=10, pady=10)
resolution_var = tk.StringVar(value="1080 (FHD)")
resolution_dropdown = ttk.Combobox(root, textvariable=resolution_var)
resolution_dropdown['values'] = [
    "2160 (4K)", 
    "1440 (2K)", 
    "1080 (FHD)", 
    "720 (HD)", 
    "480 (SD)", 
    "360 (SD)", 
    "240 (SD)", 
    "144 (SD)"
]
resolution_dropdown.grid(column=1, row=2, padx=10, pady=10)
resolution_dropdown.current(2) 

download_button = ttk.Button(root, text="Baixar", command=download_video)
download_button.grid(column=0, row=3, columnspan=2, pady=20)

# Atualiza o seletor quando o formato é trocado
format_var.trace("w", update_selector)

# Verifica/baixa FFmpeg antes de exibir a janela principal
def on_ffmpeg_ready():
    root.deiconify()

ensure_ffmpeg(on_ffmpeg_ready)
root.mainloop()
