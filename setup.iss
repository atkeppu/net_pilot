; NetPilot Inno Setup Script
; Tämä skripti luo asennusohjelman NetPilot-sovellukselle.

; Käytä ISCC-esikäsittelijää versionumeron lukemiseen tiedostosta.
#define AppVersion GetFileVersion("dist\NetPilot.exe")

[Setup]
; Perusasetukset sovellukselle
AppName=NetPilot
AppVersion={#AppVersion}
AppPublisher=Sami Turpeinen
AppPublisherURL=https://github.com/atkeppu/NetPilot
AppSupportURL=https://github.com/atkeppu/NetPilot/issues
AppUpdatesURL=https://github.com/atkeppu/NetPilot/releases

; Asennuskansio (oletus %ProgramFiles%\NetPilot)
DefaultDirName={autopf}\NetPilot
DefaultGroupName=NetPilot

; Asennusohjelman ulkoasu ja toiminta
OutputBaseFilename=NetPilot-{#AppVersion}-setup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin ; Sovellus vaatii admin-oikeudet
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\NetPilot.exe

; Pyydä käyttäjää hyväksymään lisenssi (jos sellainen on)
; LicenseFile=LICENSE.txt

; Määritellään tuetut kielet asennusohjelmalle
[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"
Name: "fi"; MessagesFile: "compiler:Languages\Finnish.isl"

; Tehtävät, joita käyttäjä voi valita asennuksen aikana
[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

; Tiedostot, jotka paketoidaan asennusohjelmaan
[Files]
; Pääohjelma
Source: "dist\NetPilot.exe"; DestDir: "{app}"; Flags: ignoreversion
; Ikonitiedosto, jota sovellus voi käyttää
Source: "icon.ico"; DestDir: "{app}"
; Voit lisätä muita tiedostoja, kuten README tai LICENSE
; Source: "README.md"; DestDir: "{app}"; Flags: isreadme

; Pikakuvakkeet, jotka luodaan
[Icons]
; Käynnistä-valikon pikakuvake
Name: "{group}\NetPilot"; Filename: "{app}\NetPilot.exe"
; Työpöydän pikakuvake (jos käyttäjä valitsee tehtävän)
Name: "{autodesktop}\NetPilot"; Filename: "{app}\NetPilot.exe"; Tasks: desktopicon
; Ohjauspaneelin "Poista asennus" -kohdan pikakuvake
Name: "{group}\{cm:UninstallProgram,NetPilot}"; Filename: "{uninstallexe}"

; Toiminnot, jotka suoritetaan asennuksen jälkeen
[Run]
; Tarjoa mahdollisuus käynnistää sovellus asennuksen päätteeksi
Filename: "{app}\NetPilot.exe"; Description: "{cm:LaunchProgram,NetPilot}"; Flags: nowait postinstall skipifsilent

; Määritellään, mitä tiedostoja ja kansioita poistetaan asennuksen poiston yhteydessä
[UninstallDelete]
; Poista sovelluksen luoma asetustiedosto
Type: files; Name: "{app}\config.ini"

; Poista lokikansio, jos se on tyhjä
Type: dirifempty; Name: "{userappdata}\NetPilot\logs"

; Poista sovelluksen juurikansio, jos se on tyhjä
Type: dirifempty; Name: "{userappdata}\NetPilot"

; Inno Setupin Pascal-skriptausosio
[Code]

// Tämä funktio tarkistaa, onko Inno Setupin suomen kielen tiedosto olemassa.
// Jos ei ole, se antaa varoituksen, mutta jatkaa englanniksi.
function InitializeSetup(): Boolean;
var
  Lang: String;
begin
  Lang := GetCurrentLanguage();
  if (Lang = 'fi') and (not FileExists(ExpandConstant('{compiler:Languages\Finnish.isl}'))) then
  begin
    MsgBox('Suomenkielistä käännöstiedostoa (Finnish.isl) ei löytynyt Inno Setupin asennuskansiosta. Asennusohjelma jatkuu englanniksi.', mbWarning, MB_OK);
  end;
  Result := True;
end;

