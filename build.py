#!/usr/bin/env python3
"""
Build script for VE2ZDX Downloader.
  macOS  : python build.py  →  dist/VE2ZDXDownloader.dmg
  Windows: python build.py  →  dist/VE2ZDXDownloaderSetup.exe (requires Inno Setup 6)
"""
import hashlib
import os
import sys
import shutil
import platform
import subprocess
import tempfile
import urllib.request
import zipfile

HANDBRAKE_VERSION = "1.11.2"
HANDBRAKE_BASE_URL = f"https://github.com/HandBrake/HandBrake/releases/download/{HANDBRAKE_VERSION}"
HANDBRAKE_ASSETS = {
    'mac': {
        'filename': f'HandBrakeCLI-{HANDBRAKE_VERSION}.dmg',
        'sha256': '14463aa81038aaa3ce421dc6cee65fd6c82fdabda040931541ccca38939299fa',
    },
    'win': {
        'filename': f'HandBrakeCLI-{HANDBRAKE_VERSION}-win-x86_64.zip',
        'sha256': '80bfe8d5f5d11cc3ef76b834add3ed4e82dee6523ffeb435c283f88b1a21f09d',
    },
}


def run(cmd):
    print(f"\n>>> {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    subprocess.run(cmd, check=True)


def clean():
    for d in ('build', 'dist'):
        if os.path.exists(d):
            shutil.rmtree(d)
            print(f"Removed {d}/")


def pyinstaller():
    run([sys.executable, '-m', 'PyInstaller', 've2zdx_downloader.spec', '--clean', '--noconfirm'])


def _sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def _download(url, dest):
    print(f"Downloading {url} ...")
    urllib.request.urlretrieve(url, dest)


def ensure_handbrake_cli(target):
    """Download HandBrakeCLI into vendor/handbrake/<target>/ if not already present."""
    asset = HANDBRAKE_ASSETS[target]
    exe_name = 'HandBrakeCLI.exe' if target == 'win' else 'HandBrakeCLI'
    dest_dir = os.path.join('vendor', 'handbrake', target)
    dest_path = os.path.join(dest_dir, exe_name)

    if os.path.isfile(dest_path):
        print(f"HandBrakeCLI already present at {dest_path}")
        return dest_path

    os.makedirs(dest_dir, exist_ok=True)
    url = f"{HANDBRAKE_BASE_URL}/{asset['filename']}"

    with tempfile.TemporaryDirectory() as tmp_dir:
        archive_path = os.path.join(tmp_dir, asset['filename'])
        _download(url, archive_path)

        digest = _sha256(archive_path)
        if digest != asset['sha256']:
            sys.exit(
                f"ERROR: HandBrakeCLI checksum mismatch for {asset['filename']}\n"
                f"  expected: {asset['sha256']}\n"
                f"  got:      {digest}"
            )
        print("Checksum OK.")

        if target == 'mac':
            mount_point = os.path.join(tmp_dir, 'mount')
            os.makedirs(mount_point, exist_ok=True)
            run(['hdiutil', 'attach', archive_path, '-mountpoint', mount_point, '-nobrowse', '-quiet'])
            try:
                shutil.copy(os.path.join(mount_point, 'HandBrakeCLI'), dest_path)
            finally:
                run(['hdiutil', 'detach', mount_point, '-quiet'])
            os.chmod(dest_path, 0o755)
        else:
            with zipfile.ZipFile(archive_path) as zf:
                zf.extract('HandBrakeCLI.exe', dest_dir)

    print(f"HandBrakeCLI ready at {dest_path}")
    return dest_path


def build_mac():
    print("\n=== macOS build ===")
    clean()
    ensure_handbrake_cli('mac')
    pyinstaller()

    app_src = 'dist/VE2ZDX Downloader.app'
    dmg_out = 'dist/VE2ZDXDownloader.dmg'
    staging = 'dist/_dmg_staging'

    if not os.path.exists(app_src):
        sys.exit(f"ERROR: {app_src} not found after build.")

    if os.path.exists(staging):
        shutil.rmtree(staging)
    os.makedirs(staging)

    shutil.copytree(app_src, os.path.join(staging, 'VE2ZDX Downloader.app'),
                    symlinks=True)
    os.symlink('/Applications', os.path.join(staging, 'Applications'))

    if os.path.exists(dmg_out):
        os.remove(dmg_out)

    run([
        'hdiutil', 'create',
        '-volname', 'VE2ZDX Downloader',
        '-srcfolder', staging,
        '-ov', '-format', 'UDZO',
        dmg_out,
    ])

    shutil.rmtree(staging)
    print(f"\n✓ Installer ready: {os.path.abspath(dmg_out)}")


def build_windows():
    print("\n=== Windows build ===")
    clean()
    ensure_handbrake_cli('win')
    pyinstaller()

    app_dir = os.path.join('dist', 'VE2ZDXDownloader')
    if not os.path.isdir(app_dir):
        sys.exit(f"ERROR: {app_dir} not found after build.")

    inno_candidates = [
        r'C:\Program Files (x86)\Inno Setup 6\ISCC.exe',
        r'C:\Program Files\Inno Setup 6\ISCC.exe',
    ]
    iscc = next((p for p in inno_candidates if os.path.exists(p)), None)

    if iscc:
        run([iscc, 'installer_windows.iss'])
        print("\n✓ Installer ready: dist\\VE2ZDXDownloaderSetup.exe")
    else:
        print(f"\n✓ Build ready: {os.path.abspath(app_dir)}")
        print("   To create an installer, install Inno Setup 6 from https://jrsoftware.org/isinfo.php")
        print("   then run:  ISCC.exe installer_windows.iss")


if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    system = platform.system()
    if system == 'Darwin':
        build_mac()
    elif system == 'Windows':
        build_windows()
    else:
        sys.exit(f"Unsupported platform: {system}")
