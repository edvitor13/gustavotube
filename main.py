import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import yt_dlp
import threading
import re

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

    # Abre o diálogo para escolher o diretório de salvamento
    save_directory = filedialog.askdirectory(title="Selecione o local para salvar o download")
    if not save_directory:
        return  # O usuário cancelou a seleção

    ydl_opts = {}

    def download_thread():
        try:
            if format_choice == "MP4":
                ydl_opts = {
                    'format': f'bestvideo[height<={resolution_choice}]+bestaudio/best',
                    'outtmpl': f'{save_directory}/%(title)s ({resolution_choice}).%(ext)s',  # Salva no diretório escolhido
                    'merge_output_format': 'mp4',
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
                    'outtmpl': f'{save_directory}/%(title)s.%(ext)s', 
                    'progress_hooks': [my_hook],
                }
            else: 
                ydl_opts = {
                    'format': 'bestvideo+bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegVideoConvertor',
                        'preferedformat': 'mp4' 
                    }],
                    'outtmpl': f'{save_directory}/%(title)s.%(ext)s', 
                    'progress_hooks': [my_hook],
                }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            messagebox.showinfo("Sucesso", "Download concluído!")
            progress_window.destroy()
            progress_window.grab_release()

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

# Configuração da janela principal
root = tk.Tk()
root.title("GustavoTube 2.0")

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

# Executa a aplicação
root.mainloop()