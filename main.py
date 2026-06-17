import os
import sys
import platform
import shutil
import urllib.request
import zipfile
import tempfile
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import yt_dlp
import threading
import re

# === Utilitários ===

def resource_path(relative):
    """Resolve caminho tanto em desenvolvimento quanto no PyInstaller one-file."""
    base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative)


def set_titlebar_color(window, color_hex):
    """Pinta a barra de título no Windows 11+ com a cor fornecida (hex #RRGGBB)."""
    if os.name != 'nt':
        return
    try:
        from ctypes import windll, c_int, byref
        hwnd = windll.user32.GetParent(window.winfo_id())
        if not hwnd:
            hwnd = window.winfo_id()
        r = int(color_hex[1:3], 16)
        g = int(color_hex[3:5], 16)
        b = int(color_hex[5:7], 16)
        colorref = r | (g << 8) | (b << 16)
        DWMWA_CAPTION_COLOR = 35
        windll.dwmapi.DwmSetWindowAttribute(
            hwnd, DWMWA_CAPTION_COLOR, byref(c_int(colorref)), 4
        )
    except Exception:
        pass


def show_about():
    about = tk.Toplevel(root)
    about.title("Sobre o GustavoTube")
    about.resizable(False, False)
    about.grab_set()

    w, h = 370, 230
    sw = about.winfo_screenwidth()
    sh = about.winfo_screenheight()
    about.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

    try:
        about.iconbitmap(resource_path('gustavotube.ico'))
    except Exception:
        pass

    set_titlebar_color(about, '#FF0000')

    tk.Label(about, text="GustavoTube 2.0", font=('', 15, 'bold'), fg='#FF0000').pack(pady=(20, 4))
    tk.Label(about, text="Baixador de vídeos e músicas do YouTube.", font=('', 10)).pack()
    tk.Label(about, text="Versão 2.0  •  06/2026", font=('', 9), fg='gray').pack(pady=(6, 14))

    link = tk.Label(
        about,
        text="vitorproductions.com/gustavotube/",
        font=('', 10, 'underline'),
        fg='#0078D7',
        cursor='hand2'
    )
    link.pack()
    link.bind('<Button-1>', lambda e: webbrowser.open('https://vitorproductions.com/gustavotube/'))

    ttk.Button(about, text="Fechar", command=about.destroy).pack(pady=(20, 0))


# === Gerenciamento do FFmpeg ===

FFMPEG_DIR = os.path.join(
    os.environ.get('APPDATA', os.path.expanduser('~')),
    'GustavoTube', 'bin'
)
ffmpeg_location = None  # None = usar ffmpeg do PATH do sistema
js_runtime = None       # Dict {runtime: config} aceito pelo yt-dlp, ex: {'deno': {'path': '/caminho'}}


def _find_local_ffmpeg():
    """Retorna FFMPEG_DIR se o binário existir lá, caso contrário None."""
    exe = 'ffmpeg.exe' if os.name == 'nt' else 'ffmpeg'
    return FFMPEG_DIR if os.path.isfile(os.path.join(FFMPEG_DIR, exe)) else None


def _find_local_deno():
    """Retorna o caminho completo do deno se existir no FFMPEG_DIR, caso contrário None."""
    exe = 'deno.exe' if os.name == 'nt' else 'deno'
    path = os.path.join(FFMPEG_DIR, exe)
    return path if os.path.isfile(path) else None


def _node_version_ok():
    """Retorna True se node está disponível e é >= 22 (mínimo do yt-dlp)."""
    if not shutil.which('node'):
        return False
    try:
        import subprocess
        out = subprocess.run(['node', '--version'], capture_output=True, text=True, timeout=5)
        major = int(out.stdout.strip().lstrip('v').split('.')[0])
        return major >= 22
    except Exception:
        return False


def _find_js_runtime():
    """Retorna (runtime_dict, needs_download).
    runtime_dict segue o formato aceito pelo yt-dlp: {'runtime': config_dict}.
    """
    if shutil.which('deno'):
        return {'deno': {}}, False
    if _node_version_ok():
        return {'node': {}}, False
    if shutil.which('qjs'):
        return {'quickjs': {}}, False
    local = _find_local_deno()
    if local:
        return {'deno': {'path': local}}, False
    return None, True


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
                jobs = [
                    ("https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip",
                     {'ffmpeg.exe', 'ffprobe.exe'}, 'zip'),
                ]
            elif sys.platform == 'darwin':
                jobs = [
                    ("https://evermeet.cx/ffmpeg/getrelease/zip", {'ffmpeg'}, 'zip'),
                    ("https://evermeet.cx/ffprobe/getrelease/zip", {'ffprobe'}, 'zip'),
                ]
            else:
                jobs = [
                    ("https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz",
                     {'ffmpeg', 'ffprobe'}, 'tar'),
                ]

            for job_idx, (url, targets, archive_type) in enumerate(jobs):
                label = f"({job_idx + 1}/{len(jobs)}) " if len(jobs) > 1 else ""
                tmp_path = os.path.join(tempfile.gettempdir(), f'ffmpeg_dl_tmp_{job_idx}')

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
                                win.after(0, lambda p=pct, d=d_mb, t=t_mb, l=label:
                                          set_ui(f"{l}Baixando... {int(p)}%  ({d:.1f} MB / {t:.1f} MB)", p))

                win.after(0, lambda l=label: set_ui(f"{l}Extraindo...", 100))

                if archive_type == 'zip':
                    with zipfile.ZipFile(tmp_path, 'r') as zf:
                        for name in zf.namelist():
                            if os.path.basename(name) in targets:
                                dest = os.path.join(FFMPEG_DIR, os.path.basename(name))
                                with zf.open(name) as src, open(dest, 'wb') as dst:
                                    dst.write(src.read())
                                if os.name != 'nt':
                                    os.chmod(dest, 0o755)
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


# === Gerenciamento do Runtime JavaScript (Deno) ===

def ensure_js_runtime(on_ready, on_error=None):
    """
    Garante que um runtime JS está disponível para o yt-dlp.
    Chama on_ready() quando pronto; faz download do Deno se necessário.
    """
    global js_runtime
    spec, needs_download = _find_js_runtime()
    if not needs_download:
        js_runtime = spec
        on_ready()
        return
    _download_deno(on_ready, on_error)


def _download_deno(on_ready, on_error=None):
    """Baixa o Deno para FFMPEG_DIR exibindo uma janela de progresso."""
    global js_runtime

    machine = platform.machine().lower()
    if os.name == 'nt':
        url = "https://github.com/denoland/deno/releases/latest/download/deno-x86_64-pc-windows-msvc.zip"
        bin_name = 'deno.exe'
    elif sys.platform == 'darwin':
        if machine in ('arm64', 'aarch64'):
            url = "https://github.com/denoland/deno/releases/latest/download/deno-aarch64-apple-darwin.zip"
        else:
            url = "https://github.com/denoland/deno/releases/latest/download/deno-x86_64-apple-darwin.zip"
        bin_name = 'deno'
    else:
        url = "https://github.com/denoland/deno/releases/latest/download/deno-x86_64-unknown-linux-gnu.zip"
        bin_name = 'deno'

    dest = os.path.join(FFMPEG_DIR, bin_name)

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
        text="Baixando Deno (runtime JavaScript necessário)...",
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
        global js_runtime
        try:
            os.makedirs(FFMPEG_DIR, exist_ok=True)
            tmp_path = os.path.join(tempfile.gettempdir(), 'deno_dl_tmp.zip')

            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=180) as resp:
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

            with zipfile.ZipFile(tmp_path, 'r') as zf:
                for name in zf.namelist():
                    if os.path.basename(name) == bin_name:
                        with zf.open(name) as src, open(dest, 'wb') as dst:
                            dst.write(src.read())
                        if os.name != 'nt':
                            os.chmod(dest, 0o755)
                        break

            os.remove(tmp_path)
            js_runtime = {'deno': {'path': dest}}

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
                        f"Falha ao baixar Deno:\n{exc}\n\n"
                        "Instale o Node.js ou o Deno manualmente e adicione ao PATH."
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

def _set_loading(loading: bool):
    """Alterna o estado de loading do botão e a barra indeterminada."""
    if loading:
        download_button.config(state='disabled', text='Buscando...')
        loading_bar.grid(column=0, row=4, columnspan=2, sticky='ew', padx=20, pady=(0, 14))
        loading_bar.start(15)
    else:
        loading_bar.stop()
        loading_bar.grid_remove()
        download_button.config(state='normal', text='Baixar')


def download_video():
    url = url_entry.get()
    format_choice = format_var.get()
    resolution_choice = resolution_var.get().split(' ')[0]

    if not url:
        messagebox.showwarning('Input Error', 'Por favor, insira uma URL do YouTube.')
        return

    _set_loading(True)

    def fetch_info_thread():
        try:
            _info_opts = {'quiet': True}
            if js_runtime:
                _info_opts['js_runtimes'] = js_runtime
            with yt_dlp.YoutubeDL(_info_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                default_filename = ydl.prepare_filename(info).rsplit('.', 1)[0]
        except Exception as e:
            root.after(0, lambda: (
                _set_loading(False),
                messagebox.showerror('Erro', f'Não foi possível obter informações do vídeo:\n{e}')
            ))
            return

        root.after(0, lambda: _open_save_dialog(default_filename, format_choice, resolution_choice, url))

    threading.Thread(target=fetch_info_thread, daemon=True).start()


def _open_save_dialog(default_filename, format_choice, resolution_choice, url):
    _set_loading(False)

    save_path = filedialog.asksaveasfilename(
        initialdir='.',
        title='Salvar arquivo como',
        initialfile=default_filename,
        defaultextension=f'.{format_choice.lower()}',
        filetypes=[(f'Arquivo {format_choice}', f'*.{format_choice.lower()}')]
    )

    if not save_path:
        return

    # === Janela de progresso ===
    progress_window = tk.Toplevel(root)
    progress_window.title('Baixando...')
    progress_window.resizable(False, False)
    progress_window.grab_set()

    w, h = 300, 100
    sw = progress_window.winfo_screenwidth()
    sh = progress_window.winfo_screenheight()
    progress_window.geometry(f'{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}')

    progress_var = tk.DoubleVar()
    progress_bar = ttk.Progressbar(progress_window, variable=progress_var, maximum=100)
    progress_bar.pack(padx=20, pady=20)

    progress_label = ttk.Label(progress_window, text='0%')
    progress_label.pack()

    def my_hook(d):
        if d['status'] == 'downloading':
            p = re.sub(r'\x1b\[[0-9;]*m', '', d['_percent_str'])
            p = float(p.replace('%', ''))
            progress_var.set(p)
            progress_label.config(text=f'{int(p)}%')
            if int(p) >= 100:
                progress_window.title('Convertendo...')
                progress_label.config(text=f'Convertendo para {format_choice}...')
            progress_window.update_idletasks()

    def download_thread():
        try:
            if format_choice == 'MP4':
                ydl_opts = {
                    'format': f'bestvideo[height<={resolution_choice}][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<={resolution_choice}]+bestaudio/best',
                    'outtmpl': save_path,
                    'merge_output_format': 'mp4',
                    'postprocessors': [{'key': 'FFmpegVideoConvertor', 'preferedformat': 'mp4'}],
                    'postprocessor_args': [
                        '-c:v', 'libx264', '-preset', 'slow', '-crf', '18',
                        '-c:a', 'aac', '-b:a', '320k',
                    ],
                    'progress_hooks': [my_hook],
                }
            else:
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
            if js_runtime:
                ydl_opts['js_runtimes'] = js_runtime

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            progress_window.after(0, lambda: (
                progress_window.destroy(),
                progress_window.grab_release(),
                messagebox.showinfo('Sucesso', 'Download concluído!'),
                open_file_directory(save_path)
            ))

        except Exception as e:
            progress_window.after(0, lambda: (
                progress_window.destroy(),
                progress_window.grab_release(),
                messagebox.showerror('Erro', f'Ocorreu um erro ao baixar o vídeo:\n{e}')
            ))

    threading.Thread(target=download_thread, daemon=True).start()

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

# Menu
menubar = tk.Menu(root)
menubar.add_command(label="Sobre", command=show_about)
root.config(menu=menubar)

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

download_button = ttk.Button(root, text='Baixar', command=download_video)
download_button.grid(column=0, row=3, columnspan=2, pady=(20, 6))

loading_bar = ttk.Progressbar(root, mode='indeterminate', length=240)
# grid_remove() mantém as configurações; só exibido durante o loading

# Atualiza o seletor quando o formato é trocado
format_var.trace("w", update_selector)

# Verifica/baixa FFmpeg e runtime JS antes de exibir a janela principal
def _show_main_window():
    try:
        root.iconbitmap(resource_path('gustavotube.ico'))
    except Exception:
        pass
    root.deiconify()
    root.after(50, lambda: set_titlebar_color(root, '#FF0000'))

def on_ffmpeg_ready():
    ensure_js_runtime(_show_main_window)

ensure_ffmpeg(on_ffmpeg_ready)
root.mainloop()
