#!/usr/bin/env python3
"""
Build script for VE2ZDX Downloader.
  macOS  : python build.py  →  dist/VE2ZDXDownloader.dmg
  Windows: python build.py  →  dist/VE2ZDXDownloaderSetup.exe (requires Inno Setup 6)
"""
import os
import sys
import shutil
import platform
import subprocess


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


def build_mac():
    print("\n=== macOS build ===")
    clean()
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
