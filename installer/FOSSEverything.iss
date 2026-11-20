; Inno Setup script for FOSSEverything.
; Requires Inno Setup 6 (https://jrsoftware.org/isinfo.php) and a prior onedir PyInstaller build at dist\FOSSEverything.
; Build both in one step with: python scripts\build_installer.py
; Version override: ISCC.exe /DMyAppVersion=1.2.3 installer\FOSSEverything.iss
;
; Silent install options:
;   FOSSEverything-Setup.exe /VERYSILENT /DIR="D:\Apps\FOSSEverything" /GROUP="Tools\FOSSEverything"
;     /TYPE=compact|full  /COMPONENTS="ctx,assoc\pdf,assoc\images"  /TASKS="desktopicon"
;     /Theme=dark|light|solarized|monokai|cyberpunk|ut_austin|ut_austin_dark  /Scale=1.25  /CURRENTUSER|/ALLUSERS

#ifndef MyAppVersion
  #define MyAppVersion "0.1.0"
#endif
#define MyAppName "FOSSEverything"
#define MyAppExeName "FOSSEverything.exe"
#define MyAppPublisher "FOSSEverything"
#define MyAppURL "https://github.com/DontKwo/FOSSEverything"

[Setup]
AppId={{E4A1B8F2-6C3D-4F9A-8E7B-2D5C9A1F3B60}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
VersionInfoVersion={#MyAppVersion}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableDirPage=no
DisableProgramGroupPage=no
DisableReadyPage=no
AllowNoIcons=yes
UsePreviousAppDir=yes
UsePreviousGroup=yes
UsePreviousSetupType=yes
UsePreviousTasks=yes
LicenseFile=..\LICENSE
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=commandline dialog
OutputDir=Output
OutputBaseFilename=FOSSEverything-Setup
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
WizardImageFile=assets\wizard-large.bmp,assets\wizard-large@2x.bmp
WizardSmallImageFile=assets\wizard-small.bmp,assets\wizard-small@2x.bmp
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
ChangesAssociations=yes
CloseApplications=yes
RestartApplications=no
SetupLogging=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Types]
Name: "full"; Description: "Full installation (app, right-click menu, Open with entries)"
Name: "compact"; Description: "Compact installation (app only)"
Name: "custom"; Description: "Custom installation"; Flags: iscustom

[Components]
Name: "main"; Description: "FOSSEverything application"; Types: full compact custom; Flags: fixed
Name: "ctx"; Description: "Explorer right-click menu: Open in FOSSEverything"; Types: full
Name: "assoc"; Description: "Show FOSSEverything in the Open with list for:"; Types: full
Name: "assoc\pdf"; Description: "PDF documents"; Types: full
Name: "assoc\images"; Description: "Images"; Types: full
Name: "assoc\media"; Description: "Audio and video"; Types: full
Name: "assoc\office"; Description: "Office documents"; Types: full
Name: "assoc\data"; Description: "Data files (JSON, YAML, CSV, XML, TSV)"; Types: full
Name: "assoc\playlists"; Description: "Playlists (M3U, M3U8)"; Types: full
Name: "assoc\model3d"; Description: "3D models (STL, OBJ, PLY, STEP, IGES)"; Types: full
Name: "assoc\markdown"; Description: "Markdown documents"; Types: full

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\FOSSEverything\*"; DestDir: "{app}"; Components: main; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Components: main
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"; Components: main
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Parameters: "--register-shell"; StatusMsg: "Registering Explorer context menu..."; Components: ctx; Flags: runhidden runasoriginaluser
Filename: "{app}\{#MyAppExeName}"; Parameters: "--configure --theme={code:GetThemeId} --ui-scale={code:GetScaleValue}"; StatusMsg: "Applying your preferences..."; Check: ShouldApplyPreferences; Flags: runhidden runasoriginaluser
Filename: "{#MyAppURL}#readme"; Description: "Open the FOSSEverything user guide"; Flags: postinstall shellexec skipifsilent unchecked
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent runasoriginaluser

[UninstallRun]
Filename: "{app}\{#MyAppExeName}"; Parameters: "--unregister-shell"; RunOnceId: "UnregisterShell"; Flags: runhidden

[Registry]
; Shared ProgID used by every selected Open with entry.
Root: HKA; Subkey: "Software\Classes\FOSSEverything.File"; ValueType: string; ValueData: "FOSSEverything File"; Flags: uninsdeletekey; Check: AnyAssociationSelected
Root: HKA; Subkey: "Software\Classes\FOSSEverything.File\DefaultIcon"; ValueType: string; ValueData: "{app}\{#MyAppExeName},0"; Check: AnyAssociationSelected
Root: HKA; Subkey: "Software\Classes\FOSSEverything.File\shell\open\command"; ValueType: string; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Check: AnyAssociationSelected
; PDF documents
Root: HKA; Subkey: "Software\Classes\.pdf\OpenWithProgids"; ValueType: string; ValueName: "FOSSEverything.File"; ValueData: ""; Flags: uninsdeletevalue; Components: assoc\pdf
; Images
Root: HKA; Subkey: "Software\Classes\.bmp\OpenWithProgids"; ValueType: string; ValueName: "FOSSEverything.File"; ValueData: ""; Flags: uninsdeletevalue; Components: assoc\images
Root: HKA; Subkey: "Software\Classes\.gif\OpenWithProgids"; ValueType: string; ValueName: "FOSSEverything.File"; ValueData: ""; Flags: uninsdeletevalue; Components: assoc\images
Root: HKA; Subkey: "Software\Classes\.ico\OpenWithProgids"; ValueType: string; ValueName: "FOSSEverything.File"; ValueData: ""; Flags: uninsdeletevalue; Components: assoc\images
Root: HKA; Subkey: "Software\Classes\.jpeg\OpenWithProgids"; ValueType: string; ValueName: "FOSSEverything.File"; ValueData: ""; Flags: uninsdeletevalue; Components: assoc\images
Root: HKA; Subkey: "Software\Classes\.jpg\OpenWithProgids"; ValueType: string; ValueName: "FOSSEverything.File"; ValueData: ""; Flags: uninsdeletevalue; Components: assoc\images
Root: HKA; Subkey: "Software\Classes\.png\OpenWithProgids"; ValueType: string; ValueName: "FOSSEverything.File"; ValueData: ""; Flags: uninsdeletevalue; Components: assoc\images
Root: HKA; Subkey: "Software\Classes\.svg\OpenWithProgids"; ValueType: string; ValueName: "FOSSEverything.File"; ValueData: ""; Flags: uninsdeletevalue; Components: assoc\images
Root: HKA; Subkey: "Software\Classes\.tif\OpenWithProgids"; ValueType: string; ValueName: "FOSSEverything.File"; ValueData: ""; Flags: uninsdeletevalue; Components: assoc\images
Root: HKA; Subkey: "Software\Classes\.tiff\OpenWithProgids"; ValueType: string; ValueName: "FOSSEverything.File"; ValueData: ""; Flags: uninsdeletevalue; Components: assoc\images
Root: HKA; Subkey: "Software\Classes\.webp\OpenWithProgids"; ValueType: string; ValueName: "FOSSEverything.File"; ValueData: ""; Flags: uninsdeletevalue; Components: assoc\images
; Audio and video
Root: HKA; Subkey: "Software\Classes\.aac\OpenWithProgids"; ValueType: string; ValueName: "FOSSEverything.File"; ValueData: ""; Flags: uninsdeletevalue; Components: assoc\media
Root: HKA; Subkey: "Software\Classes\.avi\OpenWithProgids"; ValueType: string; ValueName: "FOSSEverything.File"; ValueData: ""; Flags: uninsdeletevalue; Components: assoc\media
Root: HKA; Subkey: "Software\Classes\.flac\OpenWithProgids"; ValueType: string; ValueName: "FOSSEverything.File"; ValueData: ""; Flags: uninsdeletevalue; Components: assoc\media
Root: HKA; Subkey: "Software\Classes\.flv\OpenWithProgids"; ValueType: string; ValueName: "FOSSEverything.File"; ValueData: ""; Flags: uninsdeletevalue; Components: assoc\media
Root: HKA; Subkey: "Software\Classes\.m4a\OpenWithProgids"; ValueType: string; ValueName: "FOSSEverything.File"; ValueData: ""; Flags: uninsdeletevalue; Components: assoc\media
Root: HKA; Subkey: "Software\Classes\.m4v\OpenWithProgids"; ValueType: string; ValueName: "FOSSEverything.File"; ValueData: ""; Flags: uninsdeletevalue; Components: assoc\media
Root: HKA; Subkey: "Software\Classes\.mkv\OpenWithProgids"; ValueType: string; ValueName: "FOSSEverything.File"; ValueData: ""; Flags: uninsdeletevalue; Components: assoc\media
Root: HKA; Subkey: "Software\Classes\.mov\OpenWithProgids"; ValueType: string; ValueName: "FOSSEverything.File"; ValueData: ""; Flags: uninsdeletevalue; Components: assoc\media
Root: HKA; Subkey: "Software\Classes\.mp3\OpenWithProgids"; ValueType: string; ValueName: "FOSSEverything.File"; ValueData: ""; Flags: uninsdeletevalue; Components: assoc\media
Root: HKA; Subkey: "Software\Classes\.mp4\OpenWithProgids"; ValueType: string; ValueName: "FOSSEverything.File"; ValueData: ""; Flags: uninsdeletevalue; Components: assoc\media
Root: HKA; Subkey: "Software\Classes\.ogg\OpenWithProgids"; ValueType: string; ValueName: "FOSSEverything.File"; ValueData: ""; Flags: uninsdeletevalue; Components: assoc\media
Root: HKA; Subkey: "Software\Classes\.opus\OpenWithProgids"; ValueType: string; ValueName: "FOSSEverything.File"; ValueData: ""; Flags: uninsdeletevalue; Components: assoc\media
Root: HKA; Subkey: "Software\Classes\.wav\OpenWithProgids"; ValueType: string; ValueName: "FOSSEverything.File"; ValueData: ""; Flags: uninsdeletevalue; Components: assoc\media
Root: HKA; Subkey: "Software\Classes\.webm\OpenWithProgids"; ValueType: string; ValueName: "FOSSEverything.File"; ValueData: ""; Flags: uninsdeletevalue; Components: assoc\media
Root: HKA; Subkey: "Software\Classes\.wma\OpenWithProgids"; ValueType: string; ValueName: "FOSSEverything.File"; ValueData: ""; Flags: uninsdeletevalue; Components: assoc\media
Root: HKA; Subkey: "Software\Classes\.wmv\OpenWithProgids"; ValueType: string; ValueName: "FOSSEverything.File"; ValueData: ""; Flags: uninsdeletevalue; Components: assoc\media
; Office documents
Root: HKA; Subkey: "Software\Classes\.docm\OpenWithProgids"; ValueType: string; ValueName: "FOSSEverything.File"; ValueData: ""; Flags: uninsdeletevalue; Components: assoc\office
Root: HKA; Subkey: "Software\Classes\.docx\OpenWithProgids"; ValueType: string; ValueName: "FOSSEverything.File"; ValueData: ""; Flags: uninsdeletevalue; Components: assoc\office
Root: HKA; Subkey: "Software\Classes\.odp\OpenWithProgids"; ValueType: string; ValueName: "FOSSEverything.File"; ValueData: ""; Flags: uninsdeletevalue; Components: assoc\office
Root: HKA; Subkey: "Software\Classes\.ods\OpenWithProgids"; ValueType: string; ValueName: "FOSSEverything.File"; ValueData: ""; Flags: uninsdeletevalue; Components: assoc\office
Root: HKA; Subkey: "Software\Classes\.odt\OpenWithProgids"; ValueType: string; ValueName: "FOSSEverything.File"; ValueData: ""; Flags: uninsdeletevalue; Components: assoc\office
Root: HKA; Subkey: "Software\Classes\.pptm\OpenWithProgids"; ValueType: string; ValueName: "FOSSEverything.File"; ValueData: ""; Flags: uninsdeletevalue; Components: assoc\office
Root: HKA; Subkey: "Software\Classes\.pptx\OpenWithProgids"; ValueType: string; ValueName: "FOSSEverything.File"; ValueData: ""; Flags: uninsdeletevalue; Components: assoc\office
Root: HKA; Subkey: "Software\Classes\.xlsm\OpenWithProgids"; ValueType: string; ValueName: "FOSSEverything.File"; ValueData: ""; Flags: uninsdeletevalue; Components: assoc\office
Root: HKA; Subkey: "Software\Classes\.xlsx\OpenWithProgids"; ValueType: string; ValueName: "FOSSEverything.File"; ValueData: ""; Flags: uninsdeletevalue; Components: assoc\office
; Data files
Root: HKA; Subkey: "Software\Classes\.csv\OpenWithProgids"; ValueType: string; ValueName: "FOSSEverything.File"; ValueData: ""; Flags: uninsdeletevalue; Components: assoc\data
Root: HKA; Subkey: "Software\Classes\.json\OpenWithProgids"; ValueType: string; ValueName: "FOSSEverything.File"; ValueData: ""; Flags: uninsdeletevalue; Components: assoc\data
Root: HKA; Subkey: "Software\Classes\.tsv\OpenWithProgids"; ValueType: string; ValueName: "FOSSEverything.File"; ValueData: ""; Flags: uninsdeletevalue; Components: assoc\data
Root: HKA; Subkey: "Software\Classes\.xml\OpenWithProgids"; ValueType: string; ValueName: "FOSSEverything.File"; ValueData: ""; Flags: uninsdeletevalue; Components: assoc\data
Root: HKA; Subkey: "Software\Classes\.yaml\OpenWithProgids"; ValueType: string; ValueName: "FOSSEverything.File"; ValueData: ""; Flags: uninsdeletevalue; Components: assoc\data
Root: HKA; Subkey: "Software\Classes\.yml\OpenWithProgids"; ValueType: string; ValueName: "FOSSEverything.File"; ValueData: ""; Flags: uninsdeletevalue; Components: assoc\data
; Playlists
Root: HKA; Subkey: "Software\Classes\.m3u\OpenWithProgids"; ValueType: string; ValueName: "FOSSEverything.File"; ValueData: ""; Flags: uninsdeletevalue; Components: assoc\playlists
Root: HKA; Subkey: "Software\Classes\.m3u8\OpenWithProgids"; ValueType: string; ValueName: "FOSSEverything.File"; ValueData: ""; Flags: uninsdeletevalue; Components: assoc\playlists
; 3D models
Root: HKA; Subkey: "Software\Classes\.iges\OpenWithProgids"; ValueType: string; ValueName: "FOSSEverything.File"; ValueData: ""; Flags: uninsdeletevalue; Components: assoc\model3d
Root: HKA; Subkey: "Software\Classes\.igs\OpenWithProgids"; ValueType: string; ValueName: "FOSSEverything.File"; ValueData: ""; Flags: uninsdeletevalue; Components: assoc\model3d
Root: HKA; Subkey: "Software\Classes\.obj\OpenWithProgids"; ValueType: string; ValueName: "FOSSEverything.File"; ValueData: ""; Flags: uninsdeletevalue; Components: assoc\model3d
Root: HKA; Subkey: "Software\Classes\.ply\OpenWithProgids"; ValueType: string; ValueName: "FOSSEverything.File"; ValueData: ""; Flags: uninsdeletevalue; Components: assoc\model3d
Root: HKA; Subkey: "Software\Classes\.step\OpenWithProgids"; ValueType: string; ValueName: "FOSSEverything.File"; ValueData: ""; Flags: uninsdeletevalue; Components: assoc\model3d
Root: HKA; Subkey: "Software\Classes\.stl\OpenWithProgids"; ValueType: string; ValueName: "FOSSEverything.File"; ValueData: ""; Flags: uninsdeletevalue; Components: assoc\model3d
Root: HKA; Subkey: "Software\Classes\.stp\OpenWithProgids"; ValueType: string; ValueName: "FOSSEverything.File"; ValueData: ""; Flags: uninsdeletevalue; Components: assoc\model3d
; Markdown documents
Root: HKA; Subkey: "Software\Classes\.markdown\OpenWithProgids"; ValueType: string; ValueName: "FOSSEverything.File"; ValueData: ""; Flags: uninsdeletevalue; Components: assoc\markdown
Root: HKA; Subkey: "Software\Classes\.md\OpenWithProgids"; ValueType: string; ValueName: "FOSSEverything.File"; ValueData: ""; Flags: uninsdeletevalue; Components: assoc\markdown

[Code]
var
  OptionsPage: TWizardPage;
  ThemeCombo: TNewComboBox;
  ScaleCombo: TNewComboBox;
  KeepExistingCheck: TNewCheckBox;

function SettingsDir(): String;
begin
  Result := ExpandConstant('{%USERPROFILE|}') + '\.fosseverything';
end;

function ThemeIdAt(Index: Integer): String;
begin
  case Index of
    0: Result := 'ut_austin_dark';
    1: Result := 'dark';
    2: Result := 'light';
    3: Result := 'solarized';
    4: Result := 'monokai';
    5: Result := 'cyberpunk';
    6: Result := 'ut_austin';
  else
    Result := 'ut_austin_dark';
  end;
end;

function ScaleValueAt(Index: Integer): String;
begin
  case Index of
    0: Result := '0.9';
    1: Result := '1.0';
    2: Result := '1.1';
    3: Result := '1.25';
    4: Result := '1.5';
    5: Result := '2.0';
  else
    Result := '1.0';
  end;
end;

function ThemeIndexFor(ThemeId: String): Integer;
var
  I: Integer;
begin
  Result := 0;
  for I := 0 to 6 do
  begin
    if CompareText(ThemeIdAt(I), ThemeId) = 0 then
    begin
      Result := I;
      Exit;
    end;
  end;
end;

function ScaleIndexFor(ScaleValue: String): Integer;
var
  I: Integer;
begin
  Result := 1;
  for I := 0 to 5 do
  begin
    if ScaleValueAt(I) = ScaleValue then
    begin
      Result := I;
      Exit;
    end;
  end;
end;

function AnyAssociationSelected(): Boolean;
begin
  Result := WizardIsComponentSelected('assoc\pdf') or WizardIsComponentSelected('assoc\images')
    or WizardIsComponentSelected('assoc\media') or WizardIsComponentSelected('assoc\office')
    or WizardIsComponentSelected('assoc\data') or WizardIsComponentSelected('assoc\playlists')
    or WizardIsComponentSelected('assoc\model3d') or WizardIsComponentSelected('assoc\markdown');
end;

function HasExplicitPreferences(): Boolean;
begin
  Result := (ExpandConstant('{param:Theme|}') <> '') or (ExpandConstant('{param:Scale|}') <> '');
end;

function ShouldApplyPreferences(): Boolean;
begin
  Result := not KeepExistingCheck.Checked;
end;

function GetThemeId(Param: String): String;
begin
  Result := ThemeIdAt(ThemeCombo.ItemIndex);
end;

function GetScaleValue(Param: String): String;
begin
  Result := ScaleValueAt(ScaleCombo.ItemIndex);
end;

procedure InitializeWizard();
var
  ThemeLabel: TNewStaticText;
  ScaleLabel: TNewStaticText;
  SettingsExist: Boolean;
begin
  OptionsPage := CreateCustomPage(wpSelectTasks, 'First-run preferences',
    'Choose how FOSSEverything looks the first time it starts. Every option can be changed later in Settings.');

  ThemeLabel := TNewStaticText.Create(OptionsPage);
  ThemeLabel.Parent := OptionsPage.Surface;
  ThemeLabel.Caption := 'Theme:';
  ThemeLabel.Left := 0;
  ThemeLabel.Top := 0;

  ThemeCombo := TNewComboBox.Create(OptionsPage);
  ThemeCombo.Parent := OptionsPage.Surface;
  ThemeCombo.Style := csDropDownList;
  ThemeCombo.Left := 0;
  ThemeCombo.Top := ThemeLabel.Top + ThemeLabel.Height + ScaleY(4);
  ThemeCombo.Width := ScaleX(260);
  ThemeCombo.Items.Add('UT Austin Dark (default)');
  ThemeCombo.Items.Add('Dark');
  ThemeCombo.Items.Add('Light');
  ThemeCombo.Items.Add('Solarized');
  ThemeCombo.Items.Add('Monokai');
  ThemeCombo.Items.Add('Cyberpunk');
  ThemeCombo.Items.Add('UT Austin');
  ThemeCombo.ItemIndex := ThemeIndexFor(ExpandConstant('{param:Theme|ut_austin_dark}'));

  ScaleLabel := TNewStaticText.Create(OptionsPage);
  ScaleLabel.Parent := OptionsPage.Surface;
  ScaleLabel.Caption := 'Interface size:';
  ScaleLabel.Left := 0;
  ScaleLabel.Top := ThemeCombo.Top + ThemeCombo.Height + ScaleY(16);

  ScaleCombo := TNewComboBox.Create(OptionsPage);
  ScaleCombo.Parent := OptionsPage.Surface;
  ScaleCombo.Style := csDropDownList;
  ScaleCombo.Left := 0;
  ScaleCombo.Top := ScaleLabel.Top + ScaleLabel.Height + ScaleY(4);
  ScaleCombo.Width := ScaleX(260);
  ScaleCombo.Items.Add('90%');
  ScaleCombo.Items.Add('100% (default)');
  ScaleCombo.Items.Add('110%');
  ScaleCombo.Items.Add('125%');
  ScaleCombo.Items.Add('150%');
  ScaleCombo.Items.Add('200%');
  ScaleCombo.ItemIndex := ScaleIndexFor(ExpandConstant('{param:Scale|1.0}'));

  SettingsExist := FileExists(SettingsDir() + '\settings.json');
  KeepExistingCheck := TNewCheckBox.Create(OptionsPage);
  KeepExistingCheck.Parent := OptionsPage.Surface;
  KeepExistingCheck.Left := 0;
  KeepExistingCheck.Top := ScaleCombo.Top + ScaleCombo.Height + ScaleY(20);
  KeepExistingCheck.Width := OptionsPage.SurfaceWidth;
  KeepExistingCheck.Caption := 'Keep my existing preferences (a previous settings file was found)';
  KeepExistingCheck.Checked := SettingsExist and (not HasExplicitPreferences());
  KeepExistingCheck.Visible := SettingsExist;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if (CurUninstallStep = usPostUninstall) and (not UninstallSilent) and DirExists(SettingsDir()) then
  begin
    if MsgBox('Also delete your FOSSEverything preferences and saved data in:' + #13#10 + SettingsDir() + '?',
      mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
    begin
      DelTree(SettingsDir(), True, True, True);
    end;
  end;
end;
