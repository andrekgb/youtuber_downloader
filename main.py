import yt_dlp
import imageio_ffmpeg
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.scrolledtext import ScrolledText

class MyLogger:
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def debug(self, msg):
        self._log(msg)

    def warning(self, msg):
        self._log(msg)

    def error(self, msg):
        self._log(msg)

    def _log(self, msg):
        self.text_widget.insert(tk.END, msg + '\n')
        self.text_widget.see(tk.END)
        self.text_widget.update_idletasks()  # Ensure the text widget updates in real-time

def download_video():
    url = url_entry.get()
    if not url:
        messagebox.showerror("Error", "Please enter a video URL")
        return

    save_path = filedialog.askdirectory()
    if not save_path:
        return

    ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()

    ydl_opts = {
        'outtmpl': f'{save_path}/%(playlist_title)s/%(title)s.%(ext)s' if playlist_var.get() else f'{save_path}/%(title)s.%(ext)s',
        'format': 'bestaudio/best' if mp3_var.get() else 'bestvideo+bestaudio/best',
        'ffmpeg_location': ffmpeg_path,
        'logger': MyLogger(status_box),
        'progress_hooks': [lambda d: status_box.insert(tk.END, f"{d['status']}: {d.get('filename', '')}\n") if d['status'] == 'finished' else None],
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }] if mp3_var.get() else [],
        'noplaylist': not playlist_var.get()
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        messagebox.showinfo("Success", "Download complete!")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to download: {e}")

# GUI Setup
root = tk.Tk()
root.title("YouTube Video Downloader")

frame = tk.Frame(root, padx=20, pady=20)
frame.pack(fill=tk.BOTH, expand=True)

tk.Label(frame, text="Enter YouTube URL:").pack(pady=5)
url_entry = tk.Entry(frame, width=50)
url_entry.pack(pady=5)

mp3_var = tk.BooleanVar()
mp3_checkbox = tk.Checkbutton(frame, text="Download MP3 only", variable=mp3_var)
mp3_checkbox.pack(pady=5)

playlist_var = tk.BooleanVar()
playlist_checkbox = tk.Checkbutton(frame, text="Download Playlist", variable=playlist_var)
playlist_checkbox.pack(pady=5)

download_button = tk.Button(frame, text="Download", command=download_video)
download_button.pack(pady=10)

status_box = ScrolledText(frame, height=10, bg='black', fg='#00FF00')
status_box.pack(pady=10, fill=tk.BOTH, expand=True)

root.mainloop()