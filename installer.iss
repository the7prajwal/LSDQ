[Setup]
AppName=LSDQ
AppVersion=1.0
DefaultDirName={autopf}\LSDQ
DefaultGroupName=LSDQ
OutputDir=D:\lsdq\installer_output
OutputBaseFilename=LSDQ-Setup
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64

[Files]
Source: "D:\lsdq\dist\LSDQ.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "D:\lsdq\OllamaSetup.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall

[Run]
Filename: "{tmp}\OllamaSetup.exe"; Parameters: "/SILENT"; StatusMsg: "Installing local AI engine..."; Flags: waituntilterminated
Filename: "{app}\LSDQ.exe"; Description: "Launch LSDQ"; Flags: postinstall nowait skipifsilent

[Icons]
Name: "{group}\LSDQ"; Filename: "{app}\LSDQ.exe"
Name: "{autodesktop}\LSDQ"; Filename: "{app}\LSDQ.exe"
Name: "{group}\LSDQ Documents Folder"; Filename: "{localappdata}\LSDQ\documents"

[Messages]
FinishedLabel=LSDQ has been installed.%n%nNote: On first launch, Windows may show a "Windows protected your PC" SmartScreen warning since this app isn't code-signed yet. Click "More info" then "Run anyway" to continue — this is expected and safe.