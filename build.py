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

QUICKJS_VERSION = "0.16.1"
QUICKJS_BASE_URL = f"https://github.com/quickjs-ng/quickjs/releases/download/v{QUICKJS_VERSION}"
# yt-dlp needs a JavaScript runtime to extract YouTube videos; quickjs-ng is the
# smallest supported one (~1-2 MB), so it is bundled with the app.
QUICKJS_ASSETS = {
    ('mac', 'arm64'): {
        'filename': 'qjs-darwin-arm64',
        'sha256': '9a24e7435036906c098d539daf47bcc8e7e8ad2f3aa084a0bce9313c6c3527e0',
    },
    ('mac', 'x86_64'): {
        'filename': 'qjs-darwin-x86_64',
        'sha256': '5982a1ebb20e1a9bf6162bafd29d445823616084cfeddee8881f8d69d6e0fd74',
    },
    ('win', 'x86_64'): {
        'filename': 'qjs-windows-x86_64.exe',
        'sha256': '55a1b69cd4fdb6b0d3f8fdd910d0e89519f5330e408462084140c7b3b964fdae',
    },
}

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


def _host_arch():
    machine = platform.machine().lower()
    if machine in ('arm64', 'aarch64'):
        return 'arm64'
    return 'x86_64'


def ensure_quickjs(target, arch=None):
    """Download the qjs JavaScript runtime into vendor/quickjs/<target>/ if not already present."""
    arch = arch or _host_arch()
    asset = QUICKJS_ASSETS.get((target, arch))
    if not asset:
        sys.exit(f"ERROR: no quickjs build available for {target}/{arch}")

    exe_name = 'qjs.exe' if target == 'win' else 'qjs'
    dest_dir = os.path.join('vendor', 'quickjs', target)
    dest_path = os.path.join(dest_dir, exe_name)

    if os.path.isfile(dest_path):
        print(f"qjs already present at {dest_path}")
        return dest_path

    os.makedirs(dest_dir, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp_dir:
        download_path = os.path.join(tmp_dir, asset['filename'])
        _download(f"{QUICKJS_BASE_URL}/{asset['filename']}", download_path)

        digest = _sha256(download_path)
        if digest != asset['sha256']:
            sys.exit(
                f"ERROR: qjs checksum mismatch for {asset['filename']}\n"
                f"  expected: {asset['sha256']}\n"
                f"  got:      {digest}"
            )
        print("Checksum OK.")

        shutil.copy(download_path, dest_path)

    os.chmod(dest_path, 0o755)
    print(f"qjs ready at {dest_path}")
    return dest_path


def build_mac():
    print("\n=== macOS build ===")
    clean()
    ensure_handbrake_cli('mac')
    ensure_quickjs('mac')
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
    ensure_quickjs('win')
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
