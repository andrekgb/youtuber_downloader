import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_all

block_cipher = None

yt_dlp_datas, yt_dlp_binaries, yt_dlp_hiddenimports = collect_all('yt_dlp')

if sys.platform == 'darwin':
    handbrake_src = os.path.join('vendor', 'handbrake', 'mac', 'HandBrakeCLI')
else:
    handbrake_src = os.path.join('vendor', 'handbrake', 'win', 'HandBrakeCLI.exe')

handbrake_binaries = [(handbrake_src, '.')] if os.path.isfile(handbrake_src) else []
if not handbrake_binaries:
    print(f"WARNING: HandBrakeCLI not found at {handbrake_src} - run build.py to fetch it. "
          f"The packaged app will not be able to produce mp4 output.")

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=yt_dlp_binaries + collect_dynamic_libs('PIL') + handbrake_binaries,
    datas=[
        ('ve2zdx_logo.png', '.'),
        *collect_data_files('imageio_ffmpeg'),
        *collect_data_files('certifi'),
        *yt_dlp_datas,
    ],
    hiddenimports=[
        'PIL', 'PIL.Image', 'PIL.ImageTk',
        'tkinter', 'tkinter.filedialog', 'tkinter.messagebox',
        'tkinter.scrolledtext',
        *yt_dlp_hiddenimports,
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

if sys.platform == 'darwin':
    exe = EXE(
        pyz, a.scripts, [],
        exclude_binaries=True,
        name='VE2ZDX Downloader',
        debug=False, bootloader_ignore_signals=False,
        strip=False, upx=True, console=False,
        argv_emulation=False,
        icon='ve2zdx_logo.icns',
    )
    coll = COLLECT(
        exe, a.binaries, a.zipfiles, a.datas,
        strip=False, upx=True, upx_exclude=[],
        name='VE2ZDX Downloader',
    )
    app = BUNDLE(
        coll,
        name='VE2ZDX Downloader.app',
        icon='ve2zdx_logo.icns',
        bundle_identifier='com.ve2zdx.downloader',
        info_plist={
            'NSHighResolutionCapable': True,
            'CFBundleShortVersionString': '1.0.0',
            'LSMinimumSystemVersion': '10.13.0',
        },
    )
else:
    exe = EXE(
        pyz, a.scripts, [],
        exclude_binaries=True,
        name='VE2ZDXDownloader',
        debug=False, bootloader_ignore_signals=False,
        strip=False, upx=True, console=False,
        icon='ve2zdx_logo.ico',
    )
    coll = COLLECT(
        exe, a.binaries, a.zipfiles, a.datas,
        strip=False, upx=True, upx_exclude=[],
        name='VE2ZDXDownloader',
    )
