# Youtube Downloader
This project is a simple youtube downloader that uses the yt-dlp library to download videos/audio from youtube.
 - https://github.com/yt-dlp/yt-dlp

# Dependencies
 - pip install -r requirements.txt

# Creating Executables

## Windows Executable
To create a Windows executable with the custom icon, follow these steps:

1. Convert the PNG icon to ICO format (Windows requires ICO format for application icons):
   - Use an online converter like https://convertio.co/png-ico/
   - Or use a tool like ImageMagick: `magick convert ve2zdx_logo.png -define icon:auto-resize=64,48,32,16 ve2zdx_logo.ico`

2. Run the PyInstaller command with the ICO file:
```
pyinstaller --onefile --windowed --clean --noupx --icon=ve2zdx_logo.ico --name VE2ZDX_Youtube_Downloader main.py
```

### Command Options Explained
- `--onefile`: Creates a single executable file instead of a directory
- `--windowed`: Prevents a console window from appearing when the application runs
- `--clean`: Removes temporary files before building, which can help reduce false positives
- `--noupx`: Disables UPX compression, which often triggers antivirus warnings
- `--icon`: Specifies the icon file to use for the executable

## macOS Application
To create a macOS application with the custom icon, use the following command:

```
pyinstaller --onefile --windowed --clean --icon=ve2zdx_logo.png --name Youtube_Downloader main.py
```

### Additional macOS Steps
1. The icon file should ideally be in .icns format for macOS. You can convert the PNG to ICNS using tools like:
   - Online converters: https://cloudconvert.com/png-to-icns
   - Using the macOS command line: `sips -s format icns ve2zdx_logo.png --out ve2zdx_logo.icns`

2. If using the ICNS format, update the command:
   ```
   pyinstaller --onefile --windowed --clean --icon=ve2zdx_logo.icns --name Youtube_Downloader main.py
   ```

## Finding the Executable
After running the command, the executable will be created in the `dist` folder. You can distribute this single file to users who want to run the application without installing Python.

## Antivirus Considerations
Some antivirus software may flag the executable. This is a common false positive with PyInstaller-generated executables. If this happens:
1. Consider adding the executable to your antivirus whitelist
2. Use a trusted antivirus scanner like VirusTotal to verify the executable is safe
3. If distributing to others, provide instructions on how to handle potential antivirus warnings
