[Setup]
AppName=VE2ZDX Downloader
AppVersion=1.0
AppPublisher=VE2ZDX
AppPublisherURL=https://ve2zdx.com
DefaultDirName={autopf}\VE2ZDX Downloader
DefaultGroupName=VE2ZDX Downloader
OutputDir=dist
OutputBaseFilename=VE2ZDXDownloaderSetup
SetupIconFile=ve2zdx_logo.ico
UninstallDisplayIcon={app}\VE2ZDXDownloader.exe
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "dist\VE2ZDXDownloader\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\VE2ZDX Downloader"; Filename: "{app}\VE2ZDXDownloader.exe"
Name: "{group}\Uninstall VE2ZDX Downloader"; Filename: "{uninstallexe}"
Name: "{autodesktop}\VE2ZDX Downloader"; Filename: "{app}\VE2ZDXDownloader.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\VE2ZDXDownloader.exe"; Description: "{cm:LaunchProgram,VE2ZDX Downloader}"; Flags: nowait postinstall skipifsilent
