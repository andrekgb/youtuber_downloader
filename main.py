import yt_dlp
import imageio_ffmpeg
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
import threading
from PIL import Image, ImageTk
import os

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
        # Use tkinter's after method to update the UI from the main thread
        root.after(0, lambda: self.text_widget.insert(tk.END, msg + '\n'))
        root.after(0, lambda: self.text_widget.see(tk.END))

def download_video():
    url = url_entry.get()
    if not url:
        messagebox.showerror("Error", "Please enter a video URL")
        return

    save_path = filedialog.askdirectory()
    if not save_path:
        return

    # Disable the download button to prevent multiple clicks
    download_button.config(state=tk.DISABLED)
    status_box.insert(tk.END, "Starting download...\n")

    # Create a thread for the download process
    download_thread = threading.Thread(target=download_thread_function, args=(url, save_path))
    download_thread.daemon = True  # Thread will exit when main program exits
    download_thread.start()

def download_thread_function(url, save_path):
    ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()

    ydl_opts = {
        'outtmpl': f'{save_path}/%(playlist_title)s/%(title)s.%(ext)s' if playlist_var.get() else f'{save_path}/%(title)s.%(ext)s',
        'format': 'bestaudio/best' if mp3_var.get() else ('bestvideo[ext=mp4][vcodec^=avc]+bestaudio[ext=m4a]/best[ext=mp4]/best' if davinci_compatible_var.get() else 'bestvideo+bestaudio/best'),
        'ffmpeg_location': ffmpeg_path,
        'logger': MyLogger(status_box),
        'progress_hooks': [lambda d: status_box.insert(tk.END, f"{d['status']}: {d.get('filename', '')}\n") if d['status'] == 'finished' else None],
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }] if mp3_var.get() else ([{
            # For video downloads, ensure it's in a Davinci Resolve compatible format
            'key': 'FFmpegVideoRemuxer',
            'prefformat': 'mp4',
        }, {
            # Ensure proper merging of video and audio
            'key': 'FFmpegMerger',
            'prefformat': 'mp4',
        }] if davinci_compatible_var.get() else []),
        'merge_output_format': 'mp4' if davinci_compatible_var.get() else None,
        'noplaylist': not playlist_var.get()
    }

    # Use tkinter's after method to update the UI from the main thread
    root.after(0, lambda: status_box.insert(tk.END, "Download process started...\n"))
    if davinci_compatible_var.get():
        root.after(0, lambda: status_box.insert(tk.END, "Davinci Resolve compatibility mode enabled.\n"))

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            root.after(0, lambda: status_box.insert(tk.END, "Downloading video...\n"))
            ydl.download([url])

        # Show success message on the main thread
        root.after(0, lambda: status_box.insert(tk.END, "Download complete!\n"))

        # Create a dynamic success message based on checkbox selections

        # Handle different download type messages
        if mp3_var.get():
            success_msg = "MP3 audio extraction complete! "
        else:
            if davinci_compatible_var.get():
                success_msg = "Video download complete! The file is compatible with Davinci Resolve. "
            else:
                success_msg = "Video download complete! "

        # Add playlist information if applicable
        if playlist_var.get():
            success_msg += "Playlist processing finished."

        root.after(0, lambda: messagebox.showinfo("Success", success_msg))
    except Exception as e:
        error_msg = f"Error: {e}\n"
        error_str = str(e)
        root.after(0, lambda: status_box.insert(tk.END, error_msg))
        root.after(0, lambda msg=error_str: messagebox.showerror("Error", f"Failed to download: {msg}"))
    finally:
        # Re-enable the download button
        root.after(0, lambda: download_button.config(state=tk.NORMAL))

# GUI Setup
root = tk.Tk()
root.title("VE2ZDX YouTube Video Downloader")

# Set application icon
icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ve2zdx_logo.png")
if os.path.exists(icon_path):
    # For Windows and Linux
    icon_image = Image.open(icon_path)
    icon_photo = ImageTk.PhotoImage(icon_image)
    root.iconphoto(True, icon_photo)

    # Keep a reference to prevent garbage collection
    root.icon_photo = icon_photo

frame = tk.Frame(root, padx=20, pady=20)
frame.pack(fill=tk.BOTH, expand=True)

tk.Label(frame, text="Enter YouTube URL:").pack(pady=5)
url_entry = tk.Entry(frame, width=50)
url_entry.pack(pady=5)

mp3_var = tk.BooleanVar()
mp3_checkbox = tk.Checkbutton(frame, text="Download MP3 only", variable=mp3_var)
mp3_checkbox.pack(pady=5, anchor="w")

playlist_var = tk.BooleanVar()
playlist_checkbox = tk.Checkbutton(frame, text="Download Playlist", variable=playlist_var)
playlist_checkbox.pack(pady=5, anchor="w")

davinci_compatible_var = tk.BooleanVar()
davinci_compatible_var.set(True)  # Set to true by default
davinci_checkbox = tk.Checkbutton(frame, text="Davinci Resolve Compatible", variable=davinci_compatible_var)
davinci_checkbox.pack(pady=5, anchor="w")

download_button = tk.Button(frame, text="Download", command=download_video)
download_button.pack(pady=10)

status_box = ScrolledText(frame, height=10, bg='black', fg='#00FF00')
status_box.pack(pady=10, fill=tk.BOTH, expand=True)

root.mainloop()
