import yt_dlp
import imageio_ffmpeg
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
import threading
from PIL import Image, ImageTk
import os
import re
import shutil
import subprocess

def _find_node():
    node = shutil.which("node")
    if node:
        return node
    nvm_node = os.path.expanduser("~/.nvm/versions/node")
    if os.path.isdir(nvm_node):
        versions = sorted(os.listdir(nvm_node), reverse=True)
        for v in versions:
            candidate = os.path.join(nvm_node, v, "bin", "node")
            if os.path.isfile(candidate):
                return candidate
    return None

NODE_PATH = _find_node()

def parse_timestamp_to_seconds(ts_str):
    parts = ts_str.strip().split(':')
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
    except ValueError:
        pass
    return None

def parse_timestamps_and_callsigns(description):
    ts_pattern = r'(\d{1,2}:\d{2}:\d{2}|\d{1,2}:\d{2})'
    callsign_pattern = r'\b([A-Z]{1,2}\d{1,2}[A-Z]{1,4})\b'

    entries = []
    for line in description.split('\n'):
        ts_match = re.search(ts_pattern, line)
        cs_match = re.search(callsign_pattern, line)
        if ts_match and cs_match:
            seconds = parse_timestamp_to_seconds(ts_match.group(1))
            callsign = cs_match.group(1)
            if seconds is not None:
                entries.append((seconds, callsign))

    return sorted(entries, key=lambda x: x[0])

def slice_video_clips(video_path, entries, save_path, ffmpeg_path, log_fn):
    ext = os.path.splitext(video_path)[1] or '.mp4'

    for i, (start_sec, callsign) in enumerate(entries):
        end_sec = entries[i + 1][0] if i + 1 < len(entries) else None
        output_path = os.path.join(save_path, f"{callsign}{ext}")

        cmd = [ffmpeg_path, '-i', video_path, '-ss', str(start_sec)]
        if end_sec is not None:
            cmd += ['-to', str(end_sec)]
        cmd += ['-c', 'copy', '-y', output_path]

        end_label = f"{end_sec}s" if end_sec is not None else "end"
        log_fn(f"Cutting {callsign}: {start_sec}s -> {end_label}\n")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            log_fn(f"ffmpeg error for {callsign}: {result.stderr[-200:]}\n")


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

    download_button.config(state=tk.DISABLED)
    status_box.insert(tk.END, "Starting download...\n")

    download_thread = threading.Thread(target=download_thread_function, args=(url, save_path))
    download_thread.daemon = True
    download_thread.start()

def download_thread_function(url, save_path):
    ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()

    def log(msg):
        root.after(0, lambda m=msg: status_box.insert(tk.END, m))
        root.after(0, lambda: status_box.see(tk.END))

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
        'noplaylist': not playlist_var.get(),
        'js_runtimes': {'node': {'path': NODE_PATH}} if NODE_PATH else {},
        'remote_components': {'ejs:github'},
    }

    log("Download process started...\n")

    try:
        if slice_var.get():
            log("Fetching video description...\n")
            with yt_dlp.YoutubeDL({**ydl_opts, 'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                description = info.get('description', '') or ''

                if 've2zdx.com' not in description.lower():
                    root.after(0, lambda: messagebox.showerror(
                        "Error", "ve2zdx.com not found in video description."))
                    log("Error: ve2zdx.com not found in description.\n")
                    return

                entries = parse_timestamps_and_callsigns(description)
                if not entries:
                    root.after(0, lambda: messagebox.showerror(
                        "Error", "No timestamps with amateur radio callsigns found in description."))
                    log("Error: No valid timestamps/callsigns found in description.\n")
                    return

                log(f"Found {len(entries)} QSOs. Downloading video...\n")
                video_filename = ydl.prepare_filename(info)

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            # Locate the downloaded file (yt-dlp may merge to a different extension)
            base = os.path.splitext(video_filename)[0]
            actual_file = None
            for ext in ['.mp4', '.mkv', '.webm', '.avi', '.mov', '.m4v']:
                candidate = base + ext
                if os.path.exists(candidate):
                    actual_file = candidate
                    break
            if not actual_file and os.path.exists(video_filename):
                actual_file = video_filename

            if not actual_file:
                root.after(0, lambda: messagebox.showerror("Error", "Could not find downloaded video file."))
                log("Error: downloaded file not found on disk.\n")
                return

            log(f"Slicing into {len(entries)} clips...\n")
            slice_video_clips(actual_file, entries, save_path, ffmpeg_path, log)

            log("All clips saved!\n")
            root.after(0, lambda n=len(entries): messagebox.showinfo(
                "Success", f"Video sliced into {n} clips!"))

        else:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                log("Downloading video...\n")
                ydl.download([url])

            log("Download complete!\n")
            success_msg = "MP3 audio extraction complete!" if mp3_var.get() else "Video download complete!"
            if playlist_var.get():
                success_msg += " Playlist processing finished."
            root.after(0, lambda msg=success_msg: messagebox.showinfo("Success", msg))

    except Exception as e:
        error_str = str(e)
        log(f"Error: {error_str}\n")
        root.after(0, lambda msg=error_str: messagebox.showerror("Error", f"Failed: {msg}"))
    finally:
        root.after(0, lambda: download_button.config(state=tk.NORMAL))

# GUI Setup
root = tk.Tk()
root.title("VE2ZDX YouTube Video Downloader")

icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ve2zdx_logo.png")
if os.path.exists(icon_path):
    try:
        icon_image = Image.open(icon_path)
        icon_photo = ImageTk.PhotoImage(icon_image)
        root.iconphoto(True, icon_photo)
        root.icon_photo = icon_photo
    except Exception:
        pass

frame = tk.Frame(root, padx=20, pady=20)
frame.pack(fill=tk.BOTH, expand=True)

tk.Label(frame, text="Enter YouTube URL:").pack(pady=5)
url_entry = tk.Entry(frame, width=50, highlightthickness=2, highlightcolor='#00AA00', highlightbackground='#00AA00')
url_entry.pack(pady=5)

mp3_var = tk.BooleanVar()
mp3_checkbox = tk.Checkbutton(frame, text="Download MP3 only", variable=mp3_var)
mp3_checkbox.pack(pady=5, anchor="w")

playlist_var = tk.BooleanVar()
playlist_checkbox = tk.Checkbutton(frame, text="Download Playlist", variable=playlist_var)
playlist_checkbox.pack(pady=5, anchor="w")

slice_var = tk.BooleanVar()
slice_checkbox = tk.Checkbutton(frame, text="Slice video on timestamps", variable=slice_var)
slice_checkbox.pack(pady=5, anchor="w")

download_button = tk.Button(frame, text="Download", command=download_video)
download_button.pack(pady=10)

status_box = ScrolledText(frame, height=10, bg='black', fg='#00FF00')
status_box.pack(pady=10, fill=tk.BOTH, expand=True)

root.mainloop()
