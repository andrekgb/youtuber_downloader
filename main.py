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
import sys

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

def _find_handbrake():
    exe_name = "HandBrakeCLI.exe" if sys.platform.startswith("win") else "HandBrakeCLI"

    # PyInstaller bundle: binary is placed next to the app in _MEIPASS
    bundled = os.path.join(getattr(sys, "_MEIPASS", ""), exe_name)
    if os.path.isfile(bundled):
        return bundled

    # Dev environment: binary downloaded by build.py into vendor/handbrake/<platform>/
    vendor_dir = "win" if sys.platform.startswith("win") else "mac"
    vendor_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "vendor", "handbrake", vendor_dir, exe_name
    )
    if os.path.isfile(vendor_path):
        return vendor_path

    return shutil.which("HandBrakeCLI")

NODE_PATH = _find_node()
HANDBRAKE_PATH = _find_handbrake()

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
    callsign_pattern = r'\b(\d?[A-Z]{1,2}\d{1,3}[A-Z]{1,6})\b'

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

def build_handbrake_cmd(handbrake_path, input_path, output_path, start_sec=None, end_sec=None):
    cmd = [handbrake_path, '-i', input_path, '-o', output_path]
    if start_sec is not None:
        cmd += ['--start-at', f'duration:{start_sec}']
        if end_sec is not None:
            cmd += ['--stop-at', f'duration:{end_sec - start_sec}']
    cmd += [
        '-f', 'av_mp4', '-O',
        '-e', 'x264', '--encoder-preset', 'veryfast', '-q', '22',
        '-a', '1', '-E', 'copy', '--audio-fallback', 'aac', '-B', '160',
    ]
    return cmd


def build_clip_ranges(entries):
    """Turn a chronological (start_sec, callsign) list into (start_sec, end_sec, callsign)
    triples, where each end_sec is the next entry's start_sec (or None for the last entry)."""
    ranges = []
    for i, (start_sec, callsign) in enumerate(entries):
        end_sec = entries[i + 1][0] if i + 1 < len(entries) else None
        ranges.append((start_sec, end_sec, callsign))
    return ranges


def slice_video_clips(video_path, ranges, save_path, handbrake_path, log_fn):
    for start_sec, end_sec, callsign in ranges:
        output_path = os.path.join(save_path, f"{callsign}.mp4")

        cmd = build_handbrake_cmd(handbrake_path, video_path, output_path, start_sec, end_sec)

        end_label = f"{end_sec}s" if end_sec is not None else "end"
        log_fn(f"Cutting {callsign}: {start_sec}s -> {end_label}\n")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            log_fn(f"HandBrakeCLI error for {callsign}: {result.stderr[-300:]}\n")


def convert_to_mp4(video_path, handbrake_path, log_fn):
    if os.path.splitext(video_path)[1].lower() == '.mp4':
        return video_path

    output_path = os.path.splitext(video_path)[0] + '.mp4'
    cmd = build_handbrake_cmd(handbrake_path, video_path, output_path)

    log_fn(f"Converting {os.path.basename(video_path)} to mp4...\n")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        log_fn(f"HandBrakeCLI error converting to mp4: {result.stderr[-300:]}\n")
        return video_path

    os.remove(video_path)
    return output_path


def iter_output_filepaths(info):
    if not info:
        return
    if 'entries' in info:
        for entry in info['entries']:
            yield from iter_output_filepaths(entry)
        return
    for requested in info.get('requested_downloads') or []:
        filepath = requested.get('filepath')
        if filepath:
            yield filepath


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

    if slice_var.get() and keep_only_var.get() and not my_callsign_var.get().strip():
        messagebox.showerror("Error", "Please enter your callsign to keep only your QSO.")
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

    if not mp3_var.get() and not HANDBRAKE_PATH:
        log("Warning: HandBrakeCLI not found - output may not be converted to mp4.\n")

    try:
        if slice_var.get():
            if not HANDBRAKE_PATH:
                root.after(0, lambda: messagebox.showerror(
                    "Error", "HandBrakeCLI not found. It is required to cut the video into mp4 clips."))
                log("Error: HandBrakeCLI not found.\n")
                return

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

                ranges = build_clip_ranges(entries)

                if keep_only_var.get():
                    my_callsign = my_callsign_var.get().strip().upper()
                    ranges = [r for r in ranges if r[2] == my_callsign]
                    if not ranges:
                        root.after(0, lambda cs=my_callsign: messagebox.showerror(
                            "Error", f"No QSO found for callsign {cs} in the video description."))
                        log(f"Error: No QSO found for callsign {my_callsign}.\n")
                        return

                log(f"Found {len(ranges)} QSOs. Downloading video...\n")

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                download_info = ydl.extract_info(url, download=True)

            actual_file = next(iter_output_filepaths(download_info), None)

            if not actual_file or not os.path.exists(actual_file):
                root.after(0, lambda: messagebox.showerror("Error", "Could not find downloaded video file."))
                log("Error: downloaded file not found on disk.\n")
                return

            log(f"Slicing into {len(ranges)} clips...\n")
            slice_video_clips(actual_file, ranges, save_path, HANDBRAKE_PATH, log)

            log("All clips saved!\n")
            root.after(0, lambda n=len(ranges): messagebox.showinfo(
                "Success", f"Video sliced into {n} clips!"))

        else:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                log("Downloading video...\n")
                download_info = ydl.extract_info(url, download=True)

            if not mp3_var.get() and HANDBRAKE_PATH:
                for filepath in iter_output_filepaths(download_info):
                    if os.path.exists(filepath):
                        convert_to_mp4(filepath, HANDBRAKE_PATH, log)

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

options_frame = tk.Frame(frame)
options_frame.pack(pady=5, fill=tk.X)
options_frame.columnconfigure(0, weight=1, uniform="options")
options_frame.columnconfigure(1, weight=1, uniform="options")

audio_group = tk.LabelFrame(options_frame, text="  Audio/Music  ", padx=10, pady=5)
audio_group.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

ham_radio_group = tk.LabelFrame(options_frame, text="  Ham Radio  ", padx=10, pady=5)
ham_radio_group.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

mp3_var = tk.BooleanVar()
mp3_checkbox = tk.Checkbutton(audio_group, text="Download MP3 only", variable=mp3_var)
mp3_checkbox.pack(pady=5, anchor="w")

playlist_var = tk.BooleanVar()
playlist_checkbox = tk.Checkbutton(audio_group, text="Download Playlist", variable=playlist_var)
playlist_checkbox.pack(pady=5, anchor="w")

ham_radio_extra_frame = tk.Frame(ham_radio_group)

my_callsign_var = tk.StringVar()

def _uppercase_callsign(*_args):
    value = my_callsign_var.get()
    upper = value.upper()
    if value != upper:
        my_callsign_var.set(upper)

my_callsign_var.trace_add('write', _uppercase_callsign)

tk.Label(ham_radio_extra_frame, text="Your callsign:").pack(anchor="w")
my_callsign_entry = tk.Entry(ham_radio_extra_frame, textvariable=my_callsign_var, width=15)
my_callsign_entry.pack(anchor="w", pady=(0, 5))

keep_only_var = tk.BooleanVar()
keep_only_checkbox = tk.Checkbutton(ham_radio_extra_frame, text="Keep only my QSO", variable=keep_only_var)
keep_only_checkbox.pack(anchor="w")

def _toggle_ham_radio_extra_fields(*_args):
    if slice_var.get():
        ham_radio_extra_frame.pack(anchor="w", fill=tk.X, pady=(5, 0))
    else:
        ham_radio_extra_frame.pack_forget()

slice_var = tk.BooleanVar()
slice_var.trace_add('write', _toggle_ham_radio_extra_fields)
slice_checkbox = tk.Checkbutton(ham_radio_group, text="Slice video on timestamps", variable=slice_var)
slice_checkbox.pack(pady=5, anchor="w")

download_button = tk.Button(frame, text="Download", command=download_video)
download_button.pack(pady=10)

status_box = ScrolledText(frame, height=10, bg='black', fg='#00FF00')
status_box.pack(pady=10, fill=tk.BOTH, expand=True)

root.mainloop()
