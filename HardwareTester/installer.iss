#define AppName "NEAQ Hardware Tester"
#define AppVersion "1.0.0"
[Setup]
AppId={{5D514871-6A2F-4A05-A2D9-6A1B3FAECA4B}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=TKNL
DefaultDirName={localappdata}\Programs\NEAQ Hardware Tester
DefaultGroupName={#AppName}
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=installer
OutputBaseFilename=NEAQ-Hardware-Tester-Setup-1.0.0
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\NEAQ Hardware Tester.exe
CloseApplications=yes
[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked
[Files]
Source: "release\NEAQ Hardware Tester.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "release\config.json"; DestDir: "{app}"; Flags: onlyifdoesntexist uninsneveruninstall
Source: "release\README.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "release\*-LICENSE.txt"; DestDir: "{app}\licenses"; Flags: ignoreversion
[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\NEAQ Hardware Tester.exe"
Name: "{group}\Instructions"; Filename: "{app}\README.txt"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\NEAQ Hardware Tester.exe"; Tasks: desktopicon
[Run]
Filename: "{app}\NEAQ Hardware Tester.exe"; Description: "Launch hardware tester"; Flags: nowait postinstall skipifsilent
